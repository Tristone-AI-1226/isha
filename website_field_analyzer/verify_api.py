import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_start():
    print("Testing /trainer/start...")
    try:
        resp = requests.post(f"{BASE_URL}/trainer/start", json={"url": "https://example.com"})
        print(f"Status: {resp.status_code}, Response: {resp.json()}")
        assert resp.status_code == 200
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")

def test_command():
    print("Testing /trainer/command (wait)...")
    try:
        resp = requests.post(f"{BASE_URL}/trainer/command", json={"command": "wait", "args": "0.1"})
        print(f"Status: {resp.status_code}, Response: {resp.json()}")
        assert resp.status_code == 200
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")

def test_run_generator():
    print("Testing /run/generated_scraper (checking existence/exec)...")
    # This might fail if it tries to actually run browser etc, but we just check if it enters the endpoint
    # The generated_scraper usually connects to browser.
    try:
        resp = requests.post(f"{BASE_URL}/run/generated_scraper")
        print(f"Status: {resp.status_code}, Response: {resp.json()}")
        # It might take time or fail if headless=False implies GUI.
        # But as long as we get a response (even error from scraper) it proves API works.
        assert resp.status_code == 200
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")

if __name__ == "__main__":
    time.sleep(2) # Ensure server is up
    test_start()
    test_command()
    test_run_generator()
