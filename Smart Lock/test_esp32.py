import requests
import time
from datetime import datetime

# Configuration
BASE_URL = 'http://localhost:5000'
API_KEY = 'api123'  # Same as in config.py
HEADERS = {
    'X-API-KEY': API_KEY,
    'Content-Type': 'application/json'
}

def test_status():
    """Test API connection status"""
    response = requests.get(f'{BASE_URL}/status', headers=HEADERS)
    print("\n=== Testing Status ===")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

def test_pin_verification(pin):
    """Test PIN verification"""
    data = {
        "entrada": pin,
        "tipo": "pin"
    }
    response = requests.post(f'{BASE_URL}/verificar', headers=HEADERS, json=data)
    print(f"\n=== Testing PIN: {pin} ===")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.json()

def test_qr_verification(qr_code):
    """Test QR verification"""
    data = {
        "entrada": qr_code,
        "tipo": "qr"
    }
    response = requests.post(f'{BASE_URL}/verificar', headers=HEADERS, json=data)
    print(f"\n=== Testing QR: {qr_code} ===")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.json()

def test_2fa_verification(pin, qr_code):
    """Test 2FA verification"""
    data = {
        "pin": pin,
        "qr": qr_code
    }
    response = requests.post(f'{BASE_URL}/verificar-2fa', headers=HEADERS, json=data)
    print("\n=== Testing 2FA ===")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

def run_tests():
    """Run all tests"""
    print("Starting ESP32 Simulation Tests...")
    
    # Test 1: Check API Status
    test_status()
    
    # Test 2: Valid PIN
    test_pin_verification("12345")
    
    # Test 3: Invalid PIN
    test_pin_verification("9999")
    
    # Test 4: Valid QR Code
    test_qr_verification("QR123")
    
    # Test 5: 2FA Test
    test_2fa_verification("1234", "QR123")
    
    # Test 6: Rate Limit Test
    print("\n=== Testing Rate Limit ===")
    for i in range(12):  # Should hit rate limit after 10 requests
        print(f"Request {i+1}")
        response = test_pin_verification("1234")
        if response.get("error"):
            print(f"Rate limit hit after {i+1} requests")
            break
        time.sleep(0.5)  # Small delay between requests

if __name__ == "__main__":
    run_tests()