import requests
import concurrent.futures

# Make sure this matches the token you just generated!
TEST_TOKEN = "ff56d1f1-dfd8-49e4-9794-fe14aac4b354"
URL = "http://127.0.0.1:5000/scan"

def make_request():
    """Fires a single scan request."""
    response = requests.post(URL, json={"qr_token": TEST_TOKEN})
    return response.status_code

print("Firing 100 simultaneous check-in attempts...")

# This blasts the server with 100 requests at the exact same time
with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
    # Submit 100 identical scan requests
    results = list(executor.map(lambda _: make_request(), range(100)))

successes = results.count(200)
conflicts = results.count(409)

print(f"Successful check-ins: {successes} (Should be exactly 0 since you just checked them in!)")
print(f"Rejected duplicates: {conflicts} (Should be 100)")
print("---")
print("NOTE: To see exactly 1 success and 99 rejections, generate a brand new token using test_api.py, paste it above, and run this again.")
print(f"The hidden status codes were: {set(results)}")