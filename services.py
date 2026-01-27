"""
Business logic services for KulaPay
Loyalty points, credit eligibility, and reward calculations
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Customer, Transaction, PaymentType
from typing import Tuple, Dict


# Constants
POINTS_PER_KES = 0.1  # 1 point per 10 KES (1/10 = 0.1)
MANDAZI_COST_POINTS = 50  # Points needed for a free Mandazi
MIN_TRANSACTIONS_FOR_CREDIT = 5
MIN_SPEND_FOR_CREDIT = 500.0
CREDIT_LIMIT_PERCENTAGE = 0.20  # 20% of total spend
MAX_CREDIT_LIMIT = 300.0


def award_points(customer_phone: str, amount: float, db: Session) -> float:
    """
    Award KulaPoints to a customer based on transaction amount
    Rule: 1 point for every 10 KES spent
    
    Args:
        customer_phone: Customer phone number
        amount: Transaction amount in KES
        db: Database session
    
    Returns:
        float: Points awarded
    """
    points_earned = amount * POINTS_PER_KES
    
    # Get or create customer
    customer = db.query(Customer).filter(Customer.phone_number == customer_phone).first()
    
    if customer:
        customer.kula_points += points_earned
        db.commit()
        db.refresh(customer)
    else:
        # Customer should exist, but handle edge case
        customer = Customer(
            phone_number=customer_phone,
            kula_points=points_earned,
            credit_limit=0.0
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
    
    return points_earned


def check_credit_eligibility(customer_phone: str, db: Session) -> Dict:
    """
    Check if a customer is eligible for micro-credit (Eat Now, Pay Later)
    
    Eligibility criteria:
    - At least 5 previous transactions
    - Total historical spend exceeds 500 KES
    
    Args:
        customer_phone: Customer phone number
        db: Database session
    
    Returns:
        dict: {
            'eligible': bool,
            'transaction_count': int,
            'total_spend': float,
            'credit_limit': float,
            'message': str
        }
    """
    # Get customer's transaction history (excluding credit transactions)
    transactions = db.query(Transaction).filter(
        Transaction.customer_phone == customer_phone,
        Transaction.payment_type != PaymentType.CREDIT
    ).all()
    
    transaction_count = len(transactions)
    total_spend = sum(t.amount for t in transactions)
    
    # Check eligibility
    eligible = (
        transaction_count >= MIN_TRANSACTIONS_FOR_CREDIT and
        total_spend >= MIN_SPEND_FOR_CREDIT
    )
    
    # Calculate credit limit: 20% of total spend, capped at 300 KES
    if eligible:
        credit_limit = min(total_spend * CREDIT_LIMIT_PERCENTAGE, MAX_CREDIT_LIMIT)
    else:
        credit_limit = 0.0
    
    # Update customer's credit limit if eligible
    customer = db.query(Customer).filter(Customer.phone_number == customer_phone).first()
    if customer and eligible:
        customer.credit_limit = credit_limit
        db.commit()
        db.refresh(customer)
    
    # Generate message
    if eligible:
        message = f"Available Credit: KES {credit_limit:.2f}"
    else:
        remaining_transactions = max(0, MIN_TRANSACTIONS_FOR_CREDIT - transaction_count)
        remaining_spend = max(0, MIN_SPEND_FOR_CREDIT - total_spend)
        message = f"Keep buying to unlock credit. Need {remaining_transactions} more transactions and {remaining_spend:.2f} KES more."
    
    return {
        'eligible': eligible,
        'transaction_count': transaction_count,
        'total_spend': total_spend,
        'credit_limit': credit_limit,
        'message': message
    }


def get_customer_points_info(customer_phone: str, db: Session) -> Dict:
    """
    Get customer points information including reward progress
    
    Args:
        customer_phone: Customer phone number
        db: Database session
    
    Returns:
        dict: {
            'points': float,
            'points_to_mandazi': float,
            'message': str
        }
    """
    customer = db.query(Customer).filter(Customer.phone_number == customer_phone).first()
    
    if not customer:
        return {
            'points': 0.0,
            'points_to_mandazi': MANDAZI_COST_POINTS,
            'message': 'Customer not found.'
        }
    
    points = customer.kula_points
    points_to_mandazi = max(0, MANDAZI_COST_POINTS - points)
    
    if points >= MANDAZI_COST_POINTS:
        message = f"You have {points:.2f} KulaPoints. You can get a free Mandazi!"
    else:
        message = f"You have {points:.2f} KulaPoints. Spend {points_to_mandazi * 10:.2f} more to get a free Mandazi!"
    
    return {
        'points': points,
        'points_to_mandazi': points_to_mandazi,
        'message': message
    }


def get_customer_transaction_stats(customer_phone: str, db: Session) -> Dict:
    """
    Get customer transaction statistics
    
    Args:
        customer_phone: Customer phone number
        db: Database session
    
    Returns:
        dict: Transaction statistics
    """
    # Get all non-credit transactions
    transactions = db.query(Transaction).filter(
        Transaction.customer_phone == customer_phone,
        Transaction.payment_type != PaymentType.CREDIT
    ).all()
    
    transaction_count = len(transactions)
    total_spend = sum(t.amount for t in transactions)
    
    # Get credit transactions
    credit_transactions = db.query(Transaction).filter(
        Transaction.customer_phone == customer_phone,
        Transaction.payment_type == PaymentType.CREDIT
    ).all()
    
    credit_used = sum(t.amount for t in credit_transactions)
    
    return {
        'transaction_count': transaction_count,
        'total_spend': total_spend,
        'credit_used': credit_used
    }

