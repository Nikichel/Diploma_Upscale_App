from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from models.user import *
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class DBManager:
    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def get_db(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def add_user(self, user_data, db: AsyncSession) -> User:
        hashed_password = pwd_context.hash(user_data.password)
        db_user = User(email=user_data.email, hashed_password=hashed_password)
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    async def get_user_by_email(self, email: str, db: AsyncSession) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def update_user_balance(self, user: User, amount: int, db: AsyncSession) -> User:
        user.money += amount
        await db.commit()
        await db.refresh(user)
        return user