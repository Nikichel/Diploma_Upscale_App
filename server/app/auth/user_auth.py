from datetime import datetime, timedelta
import jwt
from jwt import PyJWTError as JWTError
from passlib.context import CryptContext
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
from models.user import *
from dotenv import load_dotenv

load_dotenv()

# Аутентификация
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserAuth:
    def __init__(self):
        self.SECRET_KEY = os.environ.get("SECRET_KEY")
        self.ALGORITHM = os.environ.get("ALGORITHM")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES"))
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

    async def get_current_user(self, token: str = Depends(oauth2_scheme), users_db: List[UserInDB] = None):
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
        except JWTError:
            raise credentials_exception

        user = next((user for user in users_db if user.email == email), None)
        if user is None:
            raise credentials_exception
        return user