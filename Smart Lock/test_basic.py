import requests
import json
from bs4 import BeautifulSoup

# Configuration
# BASE_URL = 'https://api-lock-service-1046300342556.us-central1.run.app'
BASE_URL = 'http://localhost:5000'
API_KEY = 'api123'
TEST_PIN = "4444444444"
TEST_QR = "SMARTLOCK_20250501190036"


def make_request(endpoint, data):
    headers = {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json',
        
    }

    try:
        response = requests.post(
            f"{BASE_URL}/{endpoint}",
            headers=headers,
            json=data,
        )

        if response.status_code == 200:
            print(f"Test Result: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"Error: Status code {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"Failed to parse response: {response.text}")
        print(f"Error: {str(e)}")

def test_rate_limit():
    print("\nTesting rate limit...")
    for i in range(15): 
        print(f"Request {i + 1}:")
        make_request("verificar", {"entrada": TEST_PIN, "tipo": "pin"})


def test_pin():
    print("\nTesting PIN verification...")
    make_request("verificar", {"entrada": TEST_PIN, "tipo": "pin"})

def test_qr():
    print("\nTesting QR verification...")
    make_request("verificar", {"entrada": TEST_QR, "tipo": "qr"})

def test_2fa():
    print("\nTesting 2FA verification...")
    make_request("verificar-2fa", {"pin": TEST_PIN, "qr": TEST_QR})

def status():
    print("\nTesting status...")
    headers = {
        'X-API-Key': API_KEY,  
    }

    try:
        response = requests.get(f"{BASE_URL}/status", headers=headers, timeout=5)

        if response.status_code == 200:
            print(f"Test Result: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"Error: Status code {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("Server is offline. Unable to connect to the server.")
    except requests.exceptions.Timeout:
        print("Request timed out. The server did not respond in time.")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {str(e)}")

def test_2fa_status():
    print("\nTesting 2FA status check...")
    headers = {
        'X-API-Key': API_KEY,
    }

    try:
        response = requests.get(f"{BASE_URL}/2factor/status", headers=headers, timeout=5)

        if response.status_code == 200:
            print(f"Test Result: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"Error: Status code {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("Server is offline. Unable to connect to the server.")
    except requests.exceptions.Timeout:
        print("Request timed out. The server did not respond in time.")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    try:
        print("Starting basic functionality tests...")
        test_2fa_status() 
        # test_pin()
        # status()
        # test_rate_limit()
        # test_qr()
        # test_2fa()
        print("\nTests completed!")
    except Exception as e:
        print(f"\nError during tests: {str(e)}")