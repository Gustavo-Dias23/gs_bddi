import requests, json

# Testa ISS
r = requests.get("http://api.open-notify.org/iss-now.json")
print("ISS:", r.json())

# Testa NASA NEO
r = requests.get("https://api.nasa.gov/neo/rest/v1/feed", params={
    "start_date": "2026-06-01",
    "end_date":   "2026-06-07",
    "api_key":    "DEMO_KEY"
})
print("NEO count:", r.json()["element_count"])