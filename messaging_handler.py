"""
Message handler for unified SMS/WhatsApp callback
Processes KULA commands and manages transactions
"""
from sqlalchemy.orm import Session
from typing import Dict, Optional
from models import Vendor, Customer, Transaction, PaymentType
from services import award_points, check_credit_eligibility
from messaging_service import messaging_service


def process_kula_sale(
    vendor_phone: str,
    customer_phone: str,
    item: str,
    amount: float,
    db: Session
) -> Dict:
    """
    Process a KULA sale transaction
    
    Args:
        vendor_phone: Vendor's phone number
        customer_phone: Customer's phone number
        item: Item name
        amount: Transaction amount
        db: Database session
    
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'customer_phone': str,
            'points_earned': float,
            'total_points': float,
            'credit_limit': float,
            'credit_eligible': bool
        }
    """
    try:
        # Get or create vendor
        vendor = db.query(Vendor).filter(Vendor.phone_number == vendor_phone).first()
        if not vendor:
            return {
                'success': False,
                'message': f'Vendor {vendor_phone} not found. Please register first.',
                'customer_phone': customer_phone
            }
        
        # Get or create customer
        customer = db.query(Customer).filter(Customer.phone_number == customer_phone).first()
        if not customer:
            customer = Customer(
                phone_number=customer_phone,
                kula_points=0.0,
                credit_limit=0.0
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)
        
        # Create transaction (using CASH as default payment type for messaging)
        transaction = Transaction(
            vendor_id=vendor.id,
            customer_phone=customer_phone,
            amount=amount,
            payment_type=PaymentType.CASH
        )
        db.add(transaction)
        db.commit()
        
        # Award points
        points_earned = award_points(customer_phone, amount, db)
        
        # Refresh customer to get updated points
        db.refresh(customer)
        
        # Check credit eligibility
        eligibility = check_credit_eligibility(customer_phone, db)
        
        # Refresh customer again to get updated credit limit
        db.refresh(customer)
        
        # Build response message
        response_message = (
            f"Sale Recorded! Customer {customer_phone} earned {points_earned:.2f} points. "
            f"Total points: {customer.kula_points:.2f}. "
            f"Credit Limit: {customer.credit_limit:.2f}."
        )
        
        if eligibility['eligible']:
            response_message += " Credit Eligible!"
        
        return {
            'success': True,
            'message': response_message,
            'customer_phone': customer_phone,
            'points_earned': points_earned,
            'total_points': customer.kula_points,
            'credit_limit': customer.credit_limit,
            'credit_eligible': eligibility['eligible']
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Error processing sale: {str(e)}',
            'customer_phone': customer_phone
        }

