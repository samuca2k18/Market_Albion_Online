# app/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Email verification
    is_verified = Column(Boolean, nullable=False, default=False)
    verification_token = Column(String, nullable=True, unique=True)
    verification_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    items = relationship("UserItem", back_populates="user")


class UserItem(Base):
    __tablename__ = "user_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    item_name = Column(String, nullable=False)
    display_name = Column(String, nullable=True)  # nome amigável salvo do front
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="items")
