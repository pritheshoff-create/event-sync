import requests

# The question the organizer is typing into the dashboard
payload = {
    "event_id": 1,
    "query": "How many spots are left if the capacity is 50? And how many people are no-shows so far?"
}

print("Asking the AI for event insights...")
response = requests.post("http://127.0.0.1:5000/insights", json=payload)

print("\n--- AI Response ---")
print(response.json().get("insight"))
