"""
USSD menu logic and flow handling for KulaPay
"""
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from models import Vendor, Customer, Transaction, PaymentType
from services import award_points, check_credit_eligibility, get_customer_points_info
from at_utils import repay_loan


class USSDState:
    """USSD menu states"""
    ROOT = "root"
    NEW_SALE_PHONE = "new_sale_phone"
    NEW_SALE_AMOUNT = "new_sale_amount"
    NEW_SALE_PAYMENT = "new_sale_payment"
    CHECK_POINTS = "check_points"
    CREDIT = "credit"


def parse_ussd_text(text: str) -> list:
    """
    Parse USSD text input by splitting on '*'
    Returns list of menu selections
    """
    if not text or text == "":
        return []
    return text.split("*")


def get_menu_level(text: str) -> int:
    """
    Get the current menu level based on text input
    """
    if not text or text == "":
        return 0
    return len(text.split("*"))


def handle_ussd_request(
    text: str,
    phone_number: str,
    session_id: str,
    db: Session
) -> str:
    """
    Main USSD request handler
    Returns the response message to send back
    """
    menu_selections = parse_ussd_text(text)
    menu_level = get_menu_level(text)

    # Root menu - Simple welcome for testing (no database queries)
    if menu_level == 0:
        return "END Welcome to KulaPay!"

    # Get first selection
    first_selection = menu_selections[0]

    # Route based on first selection
    if first_selection == "1":  # New Sale
        return handle_new_sale(menu_selections, menu_level, phone_number, db)
    elif first_selection == "2":  # Check Points
        return handle_check_points(menu_selections, menu_level, phone_number, db)
    elif first_selection == "3":  # Credit
        return handle_credit(menu_selections, menu_level, phone_number, db)
    else:
        return "END Invalid selection. Please try again."


def handle_new_sale(
    menu_selections: list,
    menu_level: int,
    vendor_phone: str,
    db: Session
) -> str:
    """
    Handle new sale flow:
    1. Enter customer phone
    2. Enter amount
    3. Select payment type
    4. Confirm and process
    """
    if menu_level == 1:
        return "CON Enter Customer Phone Number:"

    if menu_level == 2:
        # Store customer phone in session (in production, use Redis or similar)
        # For MVP, we'll extract it from the next request
        customer_phone = menu_selections[1]
        if not customer_phone or len(customer_phone) < 10:
            return "END Invalid phone number. Please try again."
        return "CON Enter Amount:"

    if menu_level == 3:
        # Validate amount
        try:
            amount = float(menu_selections[2])
            if amount <= 0:
                return "END Invalid amount. Please try again."
        except ValueError:
            return "END Invalid amount. Please try again."
        return "CON Select Payment Type:\n1. Cash\n2. M-Pesa"

    if menu_level == 4:
        # Process the transaction
        customer_phone = menu_selections[1]
        try:
            amount = float(menu_selections[2])
        except ValueError:
            return "END Invalid transaction. Please try again."

        payment_choice = menu_selections[3]
        if payment_choice == "1":
            payment_type = PaymentType.CASH
        elif payment_choice == "2":
            payment_type = PaymentType.MPESA
        else:
            return "END Invalid payment type. Please try again."

        # Get or create vendor
        vendor = db.query(Vendor).filter(Vendor.phone_number == vendor_phone).first()
        if not vendor:
            return "END Vendor not found. Please register first."

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

        # Award points using service (1 point per 10 KES)
        points_earned = award_points(customer_phone, amount, db)

        # Check and update credit eligibility after transaction
        eligibility = check_credit_eligibility(customer_phone, db)

        # Return success message
        return f"END Sale successful! Amount: {amount:.2f}, Payment: {payment_type.value}. Customer earned {points_earned:.2f} points."

    return "END Invalid selection. Please try again."


def handle_check_points(
    menu_selections: list,
    menu_level: int,
    phone_number: str,
    db: Session
) -> str:
    """
    Handle check points flow
    Shows points and Mandazi reward progress
    """
    if menu_level == 1:
        return "CON Enter Customer Phone Number:"

    if menu_level == 2:
        customer_phone = menu_selections[1]
        points_info = get_customer_points_info(customer_phone, db)
        
        if points_info['points'] == 0.0 and "not found" in points_info['message']:
            return "END Customer not found."
        
        return f"END {points_info['message']}"

    return "END Invalid selection. Please try again."


def handle_credit(
    menu_selections: list,
    menu_level: int,
    vendor_phone: str,
    db: Session
) -> str:
    """
    Handle credit flow (Eat Now, Pay Later)
    Flow:
    1. Enter customer phone
    2. Check eligibility and show credit options
    3. Accept loan (if eligible)
    """
    if menu_level == 1:
        return "CON Enter Customer Phone Number:"

    if menu_level == 2:
        customer_phone = menu_selections[1]
        eligibility = check_credit_eligibility(customer_phone, db)
        
        if not eligibility['eligible']:
            return f"END {eligibility['message']}"
        
        # Eligible - show credit options
        return f"CON {eligibility['message']}\n1. Accept Loan\n2. Back"

    if menu_level == 3:
        customer_phone = menu_selections[1]
        choice = menu_selections[2]
        
        if choice == "2":  # Back
            return "CON Welcome to KulaPay\n1. New Sale\n2. Check Points\n3. Credit"
        
        if choice == "1":  # Accept Loan
            # Get eligibility again to ensure we have latest credit limit
            eligibility = check_credit_eligibility(customer_phone, db)
            
            if not eligibility['eligible']:
                return "END Credit not available. Please try again."
            
            # Get vendor
            vendor = db.query(Vendor).filter(Vendor.phone_number == vendor_phone).first()
            if not vendor:
                return "END Vendor not found. Please register first."
            
            # Get customer
            customer = db.query(Customer).filter(Customer.phone_number == customer_phone).first()
            if not customer:
                return "END Customer not found."
            
            # Check if customer has available credit
            credit_available = customer.credit_limit
            
            # For MVP, we'll create a transaction with the full credit limit
            # In production, you'd ask for the loan amount
            loan_amount = credit_available
            
            # Create credit transaction
            transaction = Transaction(
                vendor_id=vendor.id,
                customer_phone=customer_phone,
                amount=loan_amount,
                payment_type=PaymentType.CREDIT
            )
            db.add(transaction)
            db.commit()
            
            # Mock loan repayment setup (in production, this would trigger actual payment processing)
            repay_loan(customer_phone, loan_amount)
            
            return f"END Loan approved! Amount: {loan_amount:.2f} KES. Repayment will be processed via M-Pesa."
        
        return "END Invalid selection. Please try again."

    return "END Invalid selection. Please try again."


def get_customer_for_sms(transaction: Transaction, db: Session) -> Optional[Customer]:
    """
    Get customer object for SMS notification
    """
    return db.query(Customer).filter(Customer.phone_number == transaction.customer_phone).first()

