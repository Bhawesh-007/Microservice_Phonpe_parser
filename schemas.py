from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import datetime
from decimal import Decimal

class AccountType(str, Enum):
    BANK = "BANK"
    CASH = "CASH"
    SAVINGS = "SAVINGS"
    WALLET = "WALLET"

class AccountBase(BaseModel):
    user_id: int
    account_type: AccountType
    balance: Decimal = Decimal("0.0")

class AccountCreate(AccountBase):
    pass

class AccountUpdate(BaseModel):
    account_type: Optional[AccountType] = None
    balance: Optional[Decimal] = None

class AccountResponse(AccountBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
