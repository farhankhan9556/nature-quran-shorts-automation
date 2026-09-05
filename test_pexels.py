import os
import requests

API_KEY = os.environ.get("PEXELS_API_KEY")

if not API_KEY:
    raise RuntimeError("PEXELS_API_KEY is missing")

response = requests.get(
    "https://api.pexels.com/v1/videos/search",
    headers={
        "Authorization": API_KEY
    },
    params={
        "query": "mountain sunrise landscape",
        "orientation": "portrait",
        "size": "medium",
        "per_page": 5
    },
    timeout=30
)

response.raise_for_status()

videos = response.json().get("videos", [])

print("Pexels connection successful")
print("Videos found:", len(videos))
