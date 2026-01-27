"""
Africa's Talking API utilities for SMS and USSD
"""
import os
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Africa's Talking credentials
AT_USERNAME = os.getenv("AT_USERNAME")
AT_API_KEY = os.getenv("AT_API_KEY")
AT_SMS_URL = "https://api.africastalking.com/version1/messaging"


def format_phone_number(phone: str) -> str:
    """
    Format phone number for Africa's Talking API
    Ensures phone number has country code (e.g., +254 for Kenya)
    
    Args:
        phone: Phone number (with or without country code)
    
    Returns:
        str: Formatted phone number with country code
    """
    # Remove any whitespace
    phone = phone.strip().replace(" ", "").replace("-", "")
    
    # If already has +, return as is
    if phone.startswith("+"):
        return phone
    
    # If starts with 0, replace with country code (Kenya: +254)
    if phone.startswith("0"):
        return "+254" + phone[1:]
    
    # If starts with country code without +, add +
    if phone.startswith("254"):
        return "+" + phone
    
    # Default: assume it's a local number, add Kenya country code
    # In production, you might want to detect country based on vendor location
    return "+254" + phone


def send_sms(phone_number: str, message: str) -> dict:
    """
    Send SMS via Africa's Talking API
    
    Args:
        phone_number: Recipient phone number (will be formatted automatically)
        message: SMS message content
    
    Returns:
        dict: API response
    """
    if not AT_USERNAME or not AT_API_KEY:
        return {
            "error": "Africa's Talking credentials not configured",
            "success": False
        }

    # Format phone number
    formatted_phone = format_phone_number(phone_number)

    headers = {
        "ApiKey": AT_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }

    data = {
        "username": AT_USERNAME,
        "to": formatted_phone,
        "message": message
    }

    try:
        response = requests.post(AT_SMS_URL, headers=headers, data=data)
        response.raise_for_status()
        
        return {
            "success": True,
            "response": response.json()
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e)
        }


def send_sale_notification(customer_phone: str, amount: float, points_earned: float) -> dict:
    """
    Send SMS notification to customer after successful sale
    
    Args:
        customer_phone: Customer phone number
        amount: Transaction amount
        points_earned: Points earned from this transaction
    
    Returns:
        dict: API response
    """
    message = (
        f"KulaPay: Your purchase of {amount:.2f} KES was successful! "
        f"You earned {points_earned:.2f} Kula Points. Thank you!"
    )
    
    return send_sms(customer_phone, message)


def repay_loan(customer_phone: str, loan_amount: float) -> dict:
    """
    Mock function to process loan repayment via Africa's Talking Payments API (Sandbox)
    
    In production, this would:
    1. Initiate M-Pesa STK push to customer
    2. Handle payment callback
    3. Update transaction status
    4. Send confirmation SMS
    
    Args:
        customer_phone: Customer phone number
        loan_amount: Loan amount to be repaid
    
    Returns:
        dict: Mock API response
    """
    # Mock implementation - in production, use AT Payments API
    # This simulates the payment processing logic
    
    formatted_phone = format_phone_number(customer_phone)
    
    # In production, you would call:
    # AT_PAYMENTS_URL = "https://payments.sandbox.africastalking.com/mobile/checkout/request"
    # With proper authentication and request payload
    
    # For now, return a mock response
    return {
        "success": True,
        "message": f"Loan repayment initiated for {loan_amount:.2f} KES",
        "customer_phone": formatted_phone,
        "status": "pending",
        "note": "This is a mock implementation. In production, integrate with AT Payments API."
    }

