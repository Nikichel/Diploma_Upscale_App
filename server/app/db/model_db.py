from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from models.user import UserPublic

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    money = Column(Integer, default=0)

    def to_public(self):
        return UserPublic(
            id=self.id,
            email=self.email,
            money=self.money
        )