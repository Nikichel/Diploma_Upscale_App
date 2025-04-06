from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager
from typing import Generator, Optional
from models.user import User, UserCreate
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
Base = declarative_base()

class DBManager:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine
        )
        Base.metadata.create_all(bind=self.engine)

    @contextmanager
    def get_db(self) -> Generator[Session, None, None]:
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    async def add_user(self, user_data: UserCreate, db: Session) -> User:
        hashed_password = pwd_context.hash(user_data.password)
        db_user = User(
            email=user_data.email,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    async def get_user_by_email(self, email: str, db: Session) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    async def update_user_balance(self, user: User, amount: int, db: Session) -> User:
        user.money += amount
        db.commit()
        db.refresh(user)
        return user

    async def deduct_credits(self, user: User, amount: int, db: Session) -> User:
        if user.money < amount:
            raise ValueError("Недостаточно средств на счете")
        user.money -= amount
        db.commit()
        db.refresh(user)
        return user