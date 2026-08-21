import requests
response = requests.post("http://127.0.0.1:5000/register", json={"event_id": 1})
print(f"Your fresh, unused token is: {response.json().get('qr_token')}")