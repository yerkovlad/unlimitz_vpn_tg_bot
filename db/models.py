from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Boolean, create_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=True, default=None)

    def __repr__(self):
        return f"<Admin id={self.id} username={self.username}>"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=True, default=None)
    balance = Column(Float, default=0)

    subscriptions = relationship("Subscription", back_populates="user")

    def __repr__(self):
        return f"<User id={self.id} username={self.username} balance={self.balance}>"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    profile_username = Column(String, nullable=False)
    profile_id = Column(String, nullable=False)
    client_uuid = Column(String, nullable=True)
    duration_start = Column(DateTime, nullable=False, default=datetime.utcnow)
    duration_end = Column(DateTime, nullable=False)
    geo = Column(String, nullable=False)
    vless_link = Column(String, nullable=True)

    user = relationship("User", back_populates="subscriptions")
    server = relationship("Server")

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    duration_months = Column(Integer, nullable=False)  # 1, 3, 6, 12
    price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Plan {self.duration_months}mo — {self.price}$>"

class Location(Base):
    __tablename__ = "locations"

    code = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

class PlanPrice(Base):
    __tablename__ = "plan_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    location_code = Column(String, ForeignKey("locations.code"), nullable=False)
    price = Column(Float, nullable=False)

class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    ip = Column(String, nullable=False)
    port = Column(Integer, nullable=False, default=2053)
    location_code = Column(String, ForeignKey("locations.code"), nullable=False)
    inbound_id = Column(Integer, nullable=False, default=1)
    max_users = Column(Integer, nullable=False, default=40)
    current_users = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=True)

    location = relationship("Location", backref="servers")

    def __repr__(self):
        return f"<Server {self.name} ({self.location_code}) {self.current_users}/{self.max_users}>"