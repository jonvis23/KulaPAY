"""
Messaging Service for KulaPay
Handles SMS and WhatsApp messaging via Africa's Talking
"""
import os
import requests
import re
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# Africa's Talking credentials
AT_USERNAME = os.getenv("AT_USERNAME")
AT_API_KEY = os.getenv("AT_API_KEY")
AT_SMS_URL = "https://api.africastalking.com/version1/messaging"
AT_WHATSAPP_URL = "https://api.africastalking.com/version1/whatsapp/message"


class MessagingService:
    """Unified messaging service for SMS and WhatsApp"""
    
    def __init__(self):
        self.username = AT_USERNAME
        self.api_key = AT_API_KEY
    
    def format_phone_number(self, phone: str) -> str:
        """
        Format phone number for Africa's Talking API
        Ensures phone number has country code (e.g., +254 for Kenya)
        """
        phone = phone.strip().replace(" ", "").replace("-", "")
        
        if phone.startswith("+"):
            return phone
        if phone.startswith("0"):
            return "+254" + phone[1:]
        if phone.startswith("254"):
            return "+" + phone
        
        return "+254" + phone
    
    def send_sms(self, phone_number: str, message: str) -> Dict:
        """
        Send SMS via Africa's Talking API
        
        Args:
            phone_number: Recipient phone number
            message: SMS message content
        
        Returns:
            dict: API response with success status
        """
        if not self.username or not self.api_key:
            return {
                "success": False,
                "error": "Africa's Talking credentials not configured"
            }
        
        formatted_phone = self.format_phone_number(phone_number)
        
        headers = {
            "ApiKey": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        data = {
            "username": self.username,
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
    
    def send_whatsapp(self, phone_number: str, message: str) -> Dict:
        """
        Send WhatsApp message via Africa's Talking API
        
        Args:
            phone_number: Recipient phone number
            message: WhatsApp message content
        
        Returns:
            dict: API response with success status
        """
        if not self.username or not self.api_key:
            return {
                "success": False,
                "error": "Africa's Talking credentials not configured"
            }
        
        formatted_phone = self.format_phone_number(phone_number)
        
        headers = {
            "ApiKey": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "username": self.username,
            "to": formatted_phone,
            "message": message
        }
        
        try:
            response = requests.post(AT_WHATSAPP_URL, headers=headers, json=payload)
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
    
    def parse_kula_command(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[float]]:
        """
        Parse KULA command from message text
        Format: "KULA [CustomerPhone] [Item] [Amount]"
        Example: "KULA 0792138852 Chapati 50"
        
        Args:
            text: Message text to parse
        
        Returns:
            tuple: (action, customer_phone, item, amount) or (None, None, None, None) if invalid
        """
        if not text:
            return None, None, None, None
        
        # Normalize text - remove extra spaces and convert to uppercase for command
        text = text.strip()
        
        # Check if it starts with KULA (case insensitive)
        if not text.upper().startswith("KULA"):
            return None, None, None, None
        
        # Remove "KULA" prefix and split the rest
        parts = text[4:].strip().split()
        
        if len(parts) < 3:
            return None, None, None, None
        
        # Extract components
        customer_phone = parts[0]
        item = " ".join(parts[1:-1])  # Item name can have multiple words
        amount_str = parts[-1]  # Last part should be the amount
        
        # Validate and parse amount
        try:
            amount = float(amount_str)
            if amount <= 0:
                return None, None, None, None
        except ValueError:
            return None, None, None, None
        
        # Validate phone number (basic check)
        if len(customer_phone) < 9:
            return None, None, None, None
        
        return "KULA", customer_phone, item, amount


# Global instance
messaging_service = MessagingService()

