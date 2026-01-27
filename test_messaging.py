"""
Test script for unified messaging callback endpoint
Tests both SMS (form data) and WhatsApp (JSON) formats
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_sms_callback():
    """Test SMS callback (form data)"""
    print("Testing SMS Callback (Form Data)...")
    print("=" * 50)
    
    url = f"{BASE_URL}/messaging/callback"
    data = {
        "from": "+254792138852",  # Vendor phone
        "to": "82107",  # Shortcode
        "text": "KULA 0711111111 Chapati 50"
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        response = requests.post(url, data=data, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print("-" * 50)
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return False


def test_whatsapp_callback():
    """Test WhatsApp callback (JSON)"""
    print("\nTesting WhatsApp Callback (JSON)...")
    print("=" * 50)
    
    url = f"{BASE_URL}/messaging/callback"
    payload = {
        "from": "+254712345678",  # Vendor phone
        "to": "+254700000000",  # WhatsApp number
        "text": "KULA 0711111111 Mandazi 30"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print("-" * 50)
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return False


def test_invalid_format():
    """Test invalid message format"""
    print("\nTesting Invalid Format...")
    print("=" * 50)
    
    url = f"{BASE_URL}/messaging/callback"
    data = {
        "from": "+254712345678",
        "to": "384",
        "text": "INVALID COMMAND"
    }
    
    try:
        response = requests.post(url, data=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print("-" * 50)
        return response.status_code == 400
    except Exception as e:
        print(f"Error: {str(e)}")
        return False


if __name__ == "__main__":
    print("Testing Unified Messaging Callback Endpoint")
    print("=" * 50)
    print("\nNote: Make sure:")
    print("1. Server is running: uvicorn main:app --reload")
    print("2. A vendor exists with phone: +254712345678")
    print("3. Database is accessible")
    print("\n")
    
    results = []
    
    # Test SMS
    results.append(("SMS Callback", test_sms_callback()))
    
    # Test WhatsApp
    results.append(("WhatsApp Callback", test_whatsapp_callback()))
    
    # Test Invalid Format
    results.append(("Invalid Format", test_invalid_format()))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    print("=" * 50)
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

