"""
SQLModel models for KulaPay USSD backend (Vendor onboarding + dashboard)
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class TransactionType(str, Enum):
    """Type of transaction recorded for a vendor."""

    SALE = "SALE"
    CREDIT_PAYMENT = "CREDIT_PAYMENT"


class Vendor(SQLModel, table=True):
    """Vendor onboarded via KulaPay USSD."""

    id: Optional[int] = Field(default=None, primary_key=True)
    phone_number: str = Field(index=True, unique=True)
    full_name: str
    business_name: str
    pin: str  # 4 digits (validated in logic layer)
    wallet_balance: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

class Transaction(SQLModel, table=True):
    """Transaction for a vendor, used to power stats/dashboard."""

    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_id: int = Field(foreign_key="vendor.id", index=True)
    amount: float
    transaction_type: str  # "SALE" or "CREDIT_PAYMENT"
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Simple FK-based link to Vendor via vendor_id; no ORM relationship required.

