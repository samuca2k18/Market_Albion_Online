from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Float, func
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    is_verified = Column(Boolean, nullable=False, default=False)
    verification_token = Column(String, nullable=True, unique=True)
    verification_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    items = relationship("UserItem", back_populates="user", cascade="all, delete-orphan")

    alerts = relationship("PriceAlert", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("UserNotification", back_populates="user", cascade="all, delete-orphan")


class UserItem(Base):
    __tablename__ = "user_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    item_name = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="items")


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    item_id = Column(String, index=True, nullable=False)
    display_name = Column(String, nullable=True)

    city = Column(String, nullable=True)
    quality = Column(Integer, nullable=True)

    target_price = Column(Float, nullable=True)

    expected_price = Column(Float, nullable=True)
    percent_below = Column(Float, nullable=True)

    use_ai_expected = Column(Boolean, default=True)
    ai_days = Column(Integer, default=7)
    ai_resolution = Column(String, default="6h")
    ai_stat = Column(String, default="median")
    ai_min_points = Column(Integer, default=10)

    last_expected_price = Column(Float, nullable=True)
    last_expected_at = Column(DateTime(timezone=True), nullable=True)

    cooldown_minutes = Column(Integer, default=60)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)

    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="alerts")


class UserNotification(Base):
    __tablename__ = "user_notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    title = Column(String, nullable=False)
    body = Column(String, nullable=False)

    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")
