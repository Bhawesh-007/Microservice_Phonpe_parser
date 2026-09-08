from sqlalchemy import Column, BigInteger, Numeric, DateTime, Enum as SQLEnum, String
from sqlalchemy.sql import func
from database import Base
import enum

class AccountType(enum.Enum):
    BANK = "BANK"
    CASH = "CASH"
    SAVINGS = "SAVINGS"
    WALLET = "WALLET"

class Account(Base):
    __tablename__ = "accounts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    account_type = Column(SQLEnum(AccountType), nullable=False)
    balance = Column(Numeric(19, 4), default=0.0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Category(Base):
    __tablename__ = "categories"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
