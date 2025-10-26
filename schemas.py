from sqlalchemy import Column, Integer, String, Float, Date,ForeignKey,DateTime
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from datetime import date
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    AccountNo = Column(Integer, unique=True, nullable=False)
    Amount = Column(Float, default=0.0)
    daily_used = Column(Float, default=2000.0)
    last_reset = Column(Date, default=date.today)
    transactions = relationship("Transaction", back_populates="user")
    
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_no = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String(20), nullable=False)  # e.g., 'credit', 'debit'
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="transactions")

class UserResponse(BaseModel):
    id: int
    username: str
    AccountNo: int
    Amount: float
    daily_used: float
    last_reset: date

    class Config:
        from_attributes = True


class TransferRequest(BaseModel):
    sender_id: int
    receiver_account: int
    amount: float
    
# class Transaction(BaseModel):
#     id: int
#     user_id: int
#     account_no: int
#     amount: float
#     transaction_type: str
#     timestamp: datetime

#     class Config:
#         orm_mode = True

class ScheduledTransferRequest(BaseModel):
    sender_id: int
    receiver_account: int
    amount: float
    scheduled_date: date
    
    class Config:
        json_schema_extra = {
            "example": {
                "sender_id": 1,
                "receiver_account": 1000000002,
                "amount": 500.0,
                "scheduled_date": "2025-10-27"
            }
        }