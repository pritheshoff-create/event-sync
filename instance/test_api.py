import requests

print("--- STEP 1: Registering a new attendee ---")
register_response = requests.post("http://127.0.0.1:5000/register", json={"event_id": 1})
token = register_response.json().get("qr_token")
print(f"Success! Generated QR Token: {token}\n")

print("--- STEP 2: Scanning the QR code at the door ---")
scan_1 = requests.post("http://127.0.0.1:5000/scan", json={"qr_token": token})
print(f"Scanner says: {scan_1.json()}\n")

print("--- STEP 3: Scanning the EXACT same QR code again ---")
scan_2 = requests.post("http://127.0.0.1:5000/scan", json={"qr_token": token})
print(f"Scanner says: {scan_2.json()}\n")