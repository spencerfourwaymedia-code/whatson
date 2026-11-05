import os
import json
import random
import requests

from bs4 import BeautifulSoup
from datetime import datetime, timedelta

EVENT_URL = "https://pro.tko.radio/presenter-daily/event-source/"

# --------------------------------------------------
# Download event page
# --------------------------------------------------

response = requests.get(EVENT_URL, timeout=30)

print(f"STATUS: {response.status_code}")

with open("debug.html", "w", encoding="utf-8") as f:
    f.write(response.text)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

# --------------------------------------------------
# Extract events
# --------------------------------------------------

events = []

for item in soup.select("li.tko-event-item"):

    title_tag = item.select_one("strong")
    location_tag = item.select_one(".tko-event-location")
    date_tag = item.select_one(".tko-event-date")

    title = (
        title_tag.get_text(strip=True)
        if title_tag
        else None
    )

    location = (
        location_tag.get_text(" ", strip=True)
        .replace("Location:", "")
        .strip()
        if location_tag
        else ""
    )

    event_time = (
        date_tag.get_text(" ", strip=True)
        if date_tag
        else ""
    )

    if title:

        events.append(
            {
                "title": title,
                "location": location,
                "time": event_time,
            }
        )

print(f"Events found: {len(events)}")

if len(events) < 5:
    raise Exception(
        f"Expected at least 5 events, only found {len(events)}"
    )

# --------------------------------------------------
# Load history
# --------------------------------------------------

try:
    with open("used_events.json", "r") as f:
        history = json.load(f)
except Exception:
    history = []

available = [
    e for e in events
    if e["title"] not in history
]

if len(available) < 5:
    available = events

selected = random.sample(available, 5)

# --------------------------------------------------
# Save updated history
# --------------------------------------------------

history.extend(
    [e["title"] for e in selected]
)

history = history[-50:]

with open("used_events.json", "w") as f:
    json.dump(history, f, indent=2)

# --------------------------------------------------
# Build bulletin
# --------------------------------------------------

tomorrow = datetime.now() + timedelta(days=1)

date_string = tomorrow.strftime("%A %d %B %Y")

script = f"Here's what's happening today - {date_string}. "

for event in selected:

    title = event["title"]
    location = event["location"]

    if location:
        script += f"{title}, taking place at {location}. "
    else:
        script += f"{title}. "

script += (
    "You can get all the latest events for where you are, "
    "from our website - visit tko dot radio for more!"
)

# --------------------------------------------------
# Save script
# --------------------------------------------------

with open("whatson.txt", "w", encoding="utf-8") as f:
    f.write(script)

print("\nSCRIPT:\n")
print(script)

# --------------------------------------------------
# Generate ElevenLabs audio
# --------------------------------------------------

voice_id = os.environ["ELEVENLABS_VOICE_ID"]

headers = {
    "xi-api-key": os.environ["ELEVENLABS_API_KEY"],
    "Content-Type": "application/json"
}

payload = {
    "text": script,
    "model_id": "eleven_multilingual_v2",
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.8
    }
}

response = requests.post(
    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
    json=payload,
    headers=headers,
    timeout=120
)

response.raise_for_status()

with open("whatson.mp3", "wb") as f:
    f.write(response.content)

print("MP3 generated successfully.")
