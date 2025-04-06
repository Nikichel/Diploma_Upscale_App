from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from typing import List, Optional
import asyncio
import gc
from model_srgan.srgan_wrapper import SRGANWrapper
import stripe
from dotenv import load_dotenv
from models.user import *
from auth.user_auth import *
from db.db_manager import DBManager
load_dotenv()

# Основное приложение
class FastAPIApp:
    def __init__(self):
        self.auth = UserAuth()
        # self.db_manager = DBManager()
        self.users_db: List[UserInDB] = []
        self.ready = False
        
        # Инициализация Stripe читайть из .env
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
        
        # Инициализация SRGAN (замените на вашу реализацию)
        self.srgan = SRGANWrapper()
        
        self.setup_routes()
        self.app.add_event_handler("shutdown", self.cleanup)
    
    async def get_current_user(self, token: str = Depends(oauth2_scheme)):
        return await self.auth.get_current_user(token, self.users_db)
    
    async def load_model(self):
        """Асинхронная загрузка модели SRGAN"""
        await self.srgan.load_model()
        self.ready = True

    async def cleanup(self):
        """Очистка ресурсов при завершении работы сервера"""
        if hasattr(self, "srgan") and hasattr(self.srgan, "model"):
            del self.srgan.model
            gc.collect()
            print("Ресурсы модели SRGAN успешно освобождены")

    def deduct_credits(self, user: UserInDB, scale_factor: int, use_decoration: bool):
        """Вычитает кредиты из баланса пользователя"""
        cost = 0
        
        # Стоимость апскейла
        if scale_factor in [2]:
            cost += 1
        elif scale_factor in [4]:
            cost += 2
        elif scale_factor == 8:
            cost += 3
        
        # Стоимость декорации
        if use_decoration:
            cost += 5
            
        # Проверяем достаточно ли средств
        if user.money < cost:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Недостаточно средств на балансе"
            )
            
        # Вычитаем средства
        user.money -= cost
        return cost

    def setup_routes(self):
        @self.app.get("/")
        async def root_path():
            return {"status": "success", "response": "root"}
    
        @self.app.post("/upscale")
        async def upscale_image(
            file: UploadFile = File(...),
            scale_factor: int = Form(4),
            use_decoration: bool = Form(False),
            current_user: UserInDB = Depends(self.get_current_user)
        ):
            if not hasattr(self.srgan, "model") or self.srgan.model is None:
                raise HTTPException(status_code=500, detail="Модель не загружена")
            
            # Вычитаем средства
            try:
                deducted = self.deduct_credits(current_user, scale_factor, use_decoration)
            except HTTPException as e:
                raise e
            
            contents = await file.read()
            
            result = await self.srgan.upscale_image(contents, scale_factor)
            
            if not result:
                raise HTTPException(status_code=500, detail="Ошибка при обработке изображения")
            
            return {
                "status": "success", 
                "image": result,
                "deducted_credits": deducted,
                "remaining_credits": current_user.money
            }

        @self.app.post("/register", response_model=UserCreate)
        async def register_user(user: UserCreate):
            if any(existing_user.email == user.email for existing_user in self.users_db):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            hashed_password = self.auth.get_password_hash(user.password)
            new_user = UserInDB(email=user.email, hashed_password=hashed_password, money=0)
            self.users_db.append(new_user)
            print(self.users_db)
            return user

        @self.app.post("/token", response_model=Token)
        async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
            user = next((user for user in self.users_db if user.email == form_data.username), None)
            print(user)
            if not user or not self.auth.verify_password(form_data.password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            access_token = self.auth.create_access_token(data={"sub": user.email})
            return {"access_token": access_token, "token_type": "bearer"}

        @self.app.get("/users/me", response_model=UserInDB)
        async def read_users_me(current_user: UserInDB = Depends(self.get_current_user)):
            return current_user

        @self.app.get("/token/validate")
        async def validate_token(current_user: UserInDB = Depends(self.get_current_user)):
            """
            Проверяет валидность токена без возврата полной информации о пользователе.
            Возвращает только статус валидации и email пользователя.
            """
            return {
                "valid": True,
                "email": current_user.email
            }

        @self.app.get("/products")
        async def get_products():
            try:
                products = stripe.Product.list(active=True, expand=['data.default_price'])
                print(len(products.data))
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
            current_user: UserInDB = Depends(self.get_current_user)
        ):
            try:
                # Получаем базовый URL
                BASE_URL = os.environ.get("BASE_URL", "http://localhost:8501")
                
                # Для отладки
                print(f"Creating checkout session with price_id: {price_id}")
                
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
                print(f"Error creating checkout session: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/payment-success")
        async def payment_success(
            session_id: str,
            product_id: str,
            current_user: UserInDB = Depends(self.get_current_user)
        ):
            try:
                # Retrieve the checkout session
                product = stripe.Product.retrieve(product_id)
                session = stripe.checkout.Session.retrieve(session_id)
                print(product)
                # Verify payment was successful
                if session.payment_status == 'paid':
                    amount = int(product.metadata.get('amount', 0))
                    print(amount)
                    
                    # Update user balance in database
                    current_user.money += amount
                    
                    return {
                        "status": "success",
                        "message": "Payment successful and balance updated",
                        "new_balance": current_user.money
                    }
                else:
                    raise HTTPException(status_code=400, detail="Payment not completed")
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/payment-canceled")
        async def payment_canceled():
            return {"status": "canceled", "message": "Payment was canceled"}
        
        @self.app.get("/current-money")
        async def current_money(
            current_user: UserInDB = Depends(self.get_current_user)
        ):
            return {
                "balance": current_user.money
            }

    def run(self, host="0.0.0.0", port=8000):
        uvicorn.run(self.app, host=host, port=port)

if __name__ == "__main__":
    app = FastAPIApp()
    app.run()