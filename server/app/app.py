from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import asyncio
import gc
from model_srgan.srgan_wrapper import SRGANWrapper
import stripe
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from db.db_manager import DBManager
from db.config import settings
from models.user import *
from auth.user_auth import UserAuth, oauth2_scheme

load_dotenv()

class FastAPIApp:
    def __init__(self):
        self.db_manager = DBManager(settings.DB_URL)
        self.auth = UserAuth(self.db_manager)
        self.ready = False
        
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
        self.stripe_public_key = os.environ.get("STRIPE_PUBLIC_KEY")
        
        self.app = FastAPI(
            title="SRGAN Upscaler API", 
            description="API для увеличения разрешения изображений с использованием SRGAN",
            version="1.0.0"
        )
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self.srgan = SRGANWrapper()
        self.setup_routes()
        self.app.add_event_handler("shutdown", self.cleanup)
    
    async def get_current_user(self, token: str = Depends(oauth2_scheme)):
        return await self.auth.get_current_user(token)

    async def load_model(self):
        await self.srgan.load_model()
        self.ready = True

    async def cleanup(self):
        if hasattr(self, "srgan") and hasattr(self.srgan, "model"):
            del self.srgan.model
            gc.collect()

    async def deduct_credits(self, user: User, scale_factor: int, use_decoration: bool):
        cost = 0
        
        # Расчет стоимости
        if scale_factor in [2]:
            cost += 1
        elif scale_factor in [4]:
            cost += 2
        elif scale_factor == 8:
            cost += 3
        
        if use_decoration:
            cost += 5
            
        async with self.db_manager.get_db() as db:
            try:
                updated_user = await self.db_manager.deduct_credits(user, cost, db)
                return cost, updated_user
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=str(e)
                )

    def setup_routes(self):
        @self.app.on_event("startup")
        async def startup():
            await self.db_manager.create_tables()
            await self.load_model()
        
        @self.app.get("/")
        async def root_path():
            return {"status": "success", "response": "root"}
    
        @self.app.post("/upscale")
        async def upscale_image(
            file: UploadFile = File(...),
            scale_factor: int = Form(4),
            use_decoration: bool = Form(False),
            current_user: User = Depends(self.get_current_user)
        ):
            if not hasattr(self.srgan, "model") or self.srgan.model is None:
                raise HTTPException(status_code=500, detail="Модель не загружена")
            
            try:
                deducted, updated_user = await self.deduct_credits(current_user, scale_factor, use_decoration)
            except HTTPException as e:
                raise e
            
            contents = await file.read()
            result = await self.srgan.upscale_image(contents, scale_factor)
            
            if not result:
                # Возвращаем кредиты при ошибке обработки
                async with self.db_manager.get_db() as db:
                    await self.db_manager.update_user_balance(updated_user, deducted, db)
                raise HTTPException(status_code=500, detail="Ошибка при обработке изображения")
            
            return {
                "status": "success", 
                "image": result,
                "deducted_credits": deducted,
                "remaining_credits": updated_user.money
            }

        @self.app.post("/register", response_model=UserPublic)
        async def register_user(user: UserCreate):
            async with self.db_manager.get_db() as db:
                existing_user = await self.db_manager.get_user_by_email(user.email, db)
                if existing_user:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered"
                    )
                
                new_user = await self.db_manager.add_user(user, db)
                return new_user.to_public()

        @self.app.post("/token", response_model=Token)
        async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
            async with self.db_manager.get_db() as db:
                user = await self.db_manager.get_user_by_email(form_data.username, db)
                
            if not user or not self.auth.verify_password(form_data.password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            access_token = self.auth.create_access_token(data={"sub": user.email})
            return {"access_token": access_token, "token_type": "bearer"}

        @self.app.get("/users/me", response_model=UserPublic)
        async def read_users_me(current_user: User = Depends(self.get_current_user)):
            return current_user.to_public()

        @self.app.get("/token/validate")
        async def validate_token(current_user: User = Depends(self.get_current_user)):
            return {"valid": True, "email": current_user.email}

        @self.app.get("/products")
        async def get_products():
            try:
                products = stripe.Product.list(active=True, expand=['data.default_price'])
                return {
                    "status": "success",
                    "products": products.data,
                    "public_key": self.stripe_public_key
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/create-checkout-session")
        async def create_checkout_session(
            price_id: str,
            current_user: User = Depends(self.get_current_user)
        ):
            try:
                BASE_URL = os.environ.get("BASE_URL", "http://localhost:8501")
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{"price": price_id, "quantity": 1}],
                    mode='payment',
                    success_url=f"{BASE_URL}?success=true",
                    cancel_url=f"{BASE_URL}?canceled=true",
                )
                return {
                    "status": "success",
                    "checkout_url": checkout_session.url,
                    "session_id": checkout_session.id
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/payment-success")
        async def payment_success(
            session_id: str,
            product_id: str,
            current_user: User = Depends(self.get_current_user)
        ):
            try:
                # 1. Получаем данные из Stripe
                product = stripe.Product.retrieve(product_id)
                session = stripe.checkout.Session.retrieve(session_id)
                
                # 2. Проверяем статус платежа
                if session.payment_status != 'paid':
                    raise HTTPException(
                        status_code=400,
                        detail="Payment not completed or failed"
                    )
                
                # 3. Получаем сумму пополнения из metadata продукта
                amount = int(product.metadata.get('amount', 0))
                if amount <= 0:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid amount in product metadata"
                    )
                
                # 4. Обновляем баланс пользователя
                async with self.db_manager.get_db() as db:
                    db_user = await db.get(User, current_user.id)
                    if not db_user:
                        raise HTTPException(
                            status_code=404,
                            detail="User not found"
                        )
                    
                    db_user.money += amount
                    await db.commit()
                    await db.refresh(db_user)
                
                return {
                    "status": "success",
                    "message": "Balance updated successfully",
                    "new_balance": db_user.money,
                    "session_id": session_id
                }
                
            except stripe.error.StripeError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stripe error: {str(e)}"
                )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Internal server error: {str(e)}"
                )

        @self.app.get("/current-money")
        async def current_money(current_user: User = Depends(self.get_current_user)):
            return {"balance": current_user.money}

    def run(self, host="0.0.0.0", port=8000):
        uvicorn.run(self.app, host=host, port=port)

if __name__ == "__main__":
    app = FastAPIApp()
    app.run()