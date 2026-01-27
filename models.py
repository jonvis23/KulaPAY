"""
SQLAlchemy models for KulaPay
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base


class PaymentType(enum.Enum):
    """Payment type enumeration"""
    CASH = "Cash"
    MPESA = "M-Pesa"
    CREDIT = "Credit"


class Vendor(Base):
    """Vendor model representing food vendors"""
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    business_name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to transactions
    transactions = relationship("Transaction", back_populates="vendor")


class Customer(Base):
    """Customer model representing customers"""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    kula_points = Column(Float, default=0.0, nullable=False)
    credit_limit = Column(Float, default=0.0, nullable=False)

    # Relationship to transactions
    transactions = relationship("Transaction", back_populates="customer")


class Transaction(Base):
    """Transaction model representing sales transactions"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    customer_phone = Column(String, ForeignKey("customers.phone_number"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_type = Column(Enum(PaymentType), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    vendor = relationship("Vendor", back_populates="transactions")
    customer = relationship("Customer", back_populates="transactions")

