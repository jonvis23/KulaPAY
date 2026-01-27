"""
Simple test script for USSD endpoint
Run this to test the USSD endpoint locally
"""
import requests

# Test the USSD endpoint
def test_ussd_root():
    """Test root menu (empty text)"""
    url = "http://localhost:8000/ussd"
    data = {
        "sessionId": "Sandbox",
        "serviceCode": "*384*11897#",
        "phoneNumber": "+254792138852",
        "text": ""
    }
    
    response = requests.post(url, data=data)
    print(f"Root Menu Test:")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Expected: 'END Welcome to KulaPay!'")
    print("-" * 50)
    return response.text == "END Welcome to KulaPay!"


if __name__ == "__main__":
    print("Testing USSD Endpoint...")
    print("=" * 50)
    
    try:
        # Test root menu
        success = test_ussd_root()
        
        if success:
            print("\n✅ Root menu test PASSED!")
        else:
            print("\n❌ Root menu test FAILED!")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server.")
        print("Make sure the server is running: uvicorn main:app --reload")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

