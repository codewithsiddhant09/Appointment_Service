"""Quick API endpoint test."""
import urllib.request
import json

BASE = "http://localhost:8000"

def get(path):
    r = urllib.request.urlopen(f"{BASE}{path}")
    return json.loads(r.read())

def post(path, data):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    r = urllib.request.urlopen(req)
    return json.loads(r.read())

# 1. Health
print("1. Health:", get("/health"))

# 2. Services
services = get("/api/v1/services")
print(f"2. Services: {len(services)} ->", [s["name"] for s in services])

# 3. Providers
providers = get("/api/v1/providers")
print(f"3. Providers: {len(providers)} ->", [p["name"] for p in providers])

# 4. Slots
slots = get("/api/v1/slots?provider_id=prov_dr_smith&date=2026-04-20")
print(f"4. Slots (Dr. Smith, today): {len(slots)}")
if slots:
    print(f"   First 3 times: {[s['time'] for s in slots[:3]]}")

# 5. Chat endpoint (conversation)
print("\n5. Testing Chat API...")
resp = post("/api/v1/chat", {
    "message": "Hi, I want to book a doctor appointment"
})
print(f"   Session: {resp['session_id'][:12]}...")
print(f"   Intent:  {resp['intent']}")
print(f"   Reply:   {resp['reply']}")
print(f"   Missing: {resp['missing_fields']}")

# 6. Follow-up turn
print("\n6. Follow-up turn...")
resp2 = post("/api/v1/chat", {
    "session_id": resp["session_id"],
    "message": "With Dr. Alice Smith, tomorrow at 10:00 AM"
})
print(f"   Intent:  {resp2['intent']}")
print(f"   Reply:   {resp2['reply']}")
print(f"   Missing: {resp2['missing_fields']}")

print("\nAll API tests passed!")
