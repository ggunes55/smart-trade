
import requests
import time
import subprocess
import sys
import os

# Start API server in background
print("Starting API Server...")
process = subprocess.Popen([sys.executable, "-m", "uvicorn", "web.backend.main:app", "--port", "8005"], 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE)

try:
    # Wait for startup
    time.sleep(5)
    
    # Test Status
    print("\nTesting /api/status...")
    try:
        resp = requests.get("http://localhost:8005/api/status")
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.json()}")
        assert resp.status_code == 200
    except Exception as e:
        print(f"Status test failed: {e}")

    # Test Watchlist
    print("\nTesting /api/watchlist...")
    try:
        resp = requests.get("http://localhost:8005/api/watchlist")
        print(f"Status Code: {resp.status_code}")
        watchlist = resp.json()
        print(f"Watchlist size: {len(watchlist)}")
        assert resp.status_code == 200
        assert isinstance(watchlist, list)
    except Exception as e:
         print(f"Watchlist test failed: {e}")
         
    # Validate Static Files
    print("\nTesting Static Files (Frontend)...")
    try:
        resp = requests.get("http://localhost:8005/")
        print(f"Status Code: {resp.status_code}")
        assert resp.status_code == 200
        assert "<title>Swing Hunter" in resp.text
    except Exception as e:
        print(f"Frontend test failed: {e}")

finally:
    print("\nStopping Server...")
    process.terminate()
    # print(process.stdout.read().decode())
    # print(process.stderr.read().decode())
