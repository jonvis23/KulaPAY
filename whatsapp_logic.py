"""
WhatsApp chat logic for KulaPay
Conversational interface (no numbering, more natural)
"""
from typing import Optional
from sqlalchemy.orm import Session
from models import Vendor, Customer, Transaction, PaymentType
from services import award_points, check_credit_eligibility, get_customer_points_info
from at_utils import repay_loan


def handle_whatsapp_message(
    message: str,
    phone_number: str,
    db: Session
) -> str:
    """
    Handle WhatsApp message - conversational interface
    
    Args:
        message: User's message (lowercased and stripped)
        phone_number: Vendor's phone number
        db: Database session
    
    Returns:
        str: Response message
    """
    message_lower = message.lower().strip()
    
    # Greeting / Help
    if message_lower in ["hi", "hello", "hey", "start", "help"]:
        return (
            "👋 Welcome to KulaPay!\n\n"
            "I can help you with:\n"
            "• New Sale - Process a customer purchase\n"
            "• Check Points - View customer loyalty points\n"
            "• Credit - Check credit eligibility\n\n"
            "Just type what you'd like to do!"
        )
    
    # New Sale
    if "sale" in message_lower or "new sale" in message_lower or "sell" in message_lower:
        return (
            "💰 New Sale\n\n"
            "Please send me:\n"
            "1. Customer phone number\n"
            "2. Amount\n"
            "3. Payment type (Cash or M-Pesa)\n\n"
            "Format: sale <phone> <amount> <cash|mpesa>\n"
            "Example: sale 0712345678 500 cash"
        )
    
    # Process sale command
    if message_lower.startswith("sale "):
        return process_sale_command(message, phone_number, db)
    
    # Check Points
    if "points" in message_lower or "check points" in message_lower:
        return (
            "⭐ Check Points\n\n"
            "Send me the customer phone number.\n"
            "Format: points <phone>\n"
            "Example: points 0712345678"
        )
    
    # Process points command
    if message_lower.startswith("points "):
        return process_points_command(message, phone_number, db)
    
    # Credit
    if "credit" in message_lower or "loan" in message_lower:
        return (
            "💳 Credit (Eat Now, Pay Later)\n\n"
            "Send me the customer phone number to check eligibility.\n"
            "Format: credit <phone>\n"
            "Example: credit 0712345678"
        )
    
    # Process credit command
    if message_lower.startswith("credit "):
        return process_credit_command(message, phone_number, db)
    
    # Default response
    return (
        "I didn't understand that. 😅\n\n"
        "Try:\n"
        "• 'sale' - Process a new sale\n"
        "• 'points' - Check customer points\n"
        "• 'credit' - Check credit eligibility\n"
        "• 'help' - See all options"
    )


def process_sale_command(message: str, vendor_phone: str, db: Session) -> str:
    """
    Process sale command: sale <phone> <amount> <cash|mpesa>
    """
    parts = message.split()
    
    if len(parts) < 4:
        return "❌ Invalid format. Use: sale <phone> <amount> <cash|mpesa>"
    
    try:
        customer_phone = parts[1]
        amount = float(parts[2])
        payment_str = parts[3].lower()
        
        if amount <= 0:
            return "❌ Amount must be greater than 0"
        
        if payment_str == "cash":
            payment_type = PaymentType.CASH
        elif payment_str in ["mpesa", "m-pesa", "m pesa"]:
            payment_type = PaymentType.MPESA
        else:
            return "❌ Payment type must be 'cash' or 'mpesa'"
        
        # Get vendor
        vendor = db.query(Vendor).filter(Vendor.phone_number == vendor_phone).first()
        if not vendor:
            return "❌ Vendor not found. Please register first."
        
        # Get or create customer
        customer = db.query(Customer).filter(Customer.phone_number == customer_phone).first()
        if not customer:
            customer = Customer(phone_number=customer_phone, kula_points=0.0, credit_limit=0.0)
            db.add(customer)
            db.commit()
            db.refresh(customer)
        
        # Create transaction
        transaction = Transaction(
            vendor_id=vendor.id,
            customer_phone=customer_phone,
            amount=amount,
            payment_type=payment_type
        )
        db.add(transaction)
        db.commit()
        
        # Award points
        points_earned = award_points(customer_phone, amount, db)
        
        # Check credit eligibility
        eligibility = check_credit_eligibility(customer_phone, db)
        
        return (
            f"✅ Sale successful!\n\n"
            f"Amount: {amount:.2f} KES\n"
            f"Payment: {payment_type.value}\n"
            f"Points earned: {points_earned:.2f}\n\n"
            f"Customer now has {customer.kula_points:.2f} total points."
        )
        
    except ValueError:
        return "❌ Invalid amount. Please use a number."
    except Exception as e:
        return f"❌ Error processing sale: {str(e)}"


def process_points_command(message: str, vendor_phone: str, db: Session) -> str:
    """
    Process points command: points <phone>
    """
    parts = message.split()
    
    if len(parts) < 2:
        return "❌ Invalid format. Use: points <phone>"
    
    customer_phone = parts[1]
    points_info = get_customer_points_info(customer_phone, db)
    
    if points_info['points'] == 0.0 and "not found" in points_info['message']:
        return "❌ Customer not found."
    
    return f"⭐ {points_info['message']}"


def process_credit_command(message: str, vendor_phone: str, db: Session) -> str:
    """
    Process credit command: credit <phone> [accept]
    """
    parts = message.split()
    
    if len(parts) < 2:
        return "❌ Invalid format. Use: credit <phone>"
    
    customer_phone = parts[1]
    eligibility = check_credit_eligibility(customer_phone, db)
    
    if not eligibility['eligible']:
        return f"ℹ️ {eligibility['message']}"
    
    # If "accept" is in the message, process the loan
    if len(parts) >= 3 and parts[2].lower() == "accept":
        # Get vendor
        vendor = db.query(Vendor).filter(Vendor.phone_number == vendor_phone).first()
        if not vendor:
            return "❌ Vendor not found."
        
        # Get customer
        customer = db.query(Customer).filter(Customer.phone_number == customer_phone).first()
        if not customer:
            return "❌ Customer not found."
        
        loan_amount = customer.credit_limit
        
        # Create credit transaction
        transaction = Transaction(
            vendor_id=vendor.id,
            customer_phone=customer_phone,
            amount=loan_amount,
            payment_type=PaymentType.CREDIT
        )
        db.add(transaction)
        db.commit()
        
        # Mock loan repayment
        repay_loan(customer_phone, loan_amount)
        
        return (
            f"✅ Loan approved!\n\n"
            f"Amount: {loan_amount:.2f} KES\n"
            f"Repayment will be processed via M-Pesa."
        )
    
    # Show eligibility and instructions
    return (
        f"💳 {eligibility['message']}\n\n"
        f"To accept the loan, reply:\n"
        f"credit {customer_phone} accept"
    )

