from datetime import datetime, timedelta
import jwt
from jwt import PyJWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from models.user import *
from db.db_manager import DBManager
from passlib.context import CryptContext
import os
from dotenv import load_dotenv
from db.model_db import User

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserAuth:
    def __init__(self, db_manager: DBManager):
        self.db_manager = db_manager
        self.SECRET_KEY = os.getenv("SECRET_KEY", "secret")
        self.ALGORITHM = os.getenv("ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def create_access_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)

    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                raise credentials_exception
        except PyJWTError:
            raise credentials_exception

        async with self.db_manager.get_db() as db:
            user = await self.db_manager.get_user_by_email(email, db)
        
        if user is None:
            raise credentials_exception
        return user