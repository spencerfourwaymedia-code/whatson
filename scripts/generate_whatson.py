import os
import json
import random
import requests

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from google import genai

EVENT_URL = "https://pro.tko.radio/presenter-daily/event-source/"

# --------------------------------------------------
# Download page
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
        f"Only found {len(events)} events."
    )

# --------------------------------------------------
# Event history
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

history.extend(
    [e["title"] for e in selected]
)

history = history[-50:]

with open("used_events.json", "w") as f:
    json.dump(history, f, indent=2)

# --------------------------------------------------
# Spoken date
# --------------------------------------------------

tomorrow = datetime.now() + timedelta(days=1)

day = tomorrow.day

if 11 <= day <= 13:
    suffix = "th"
else:
    suffix = {
        1: "st",
        2: "nd",
        3: "rd"
    }.get(day % 10, "th")

spoken_date = (
    f"{tomorrow.strftime('%A')} "
    f"the {day}{suffix} of "
    f"{tomorrow.strftime('%B')}"
)

# --------------------------------------------------
# Event list for Gemini
# --------------------------------------------------

event_list = ""

for event in selected:

    event_list += f"""
Title: {event['title']}
Location: {event['location']}
Time: {event['time']}

"""

# --------------------------------------------------
# Gemini
# --------------------------------------------------

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)

prompt = f"""
You are a professional British radio presenter.

Write a 45-second What's On guide for TKO Radio.

This will be read aloud by an AI voice.

Write for the ear, not the eye.

Requirements:

- Sound like local commercial radio.
- Friendly and conversational.
- Do not sound like a list.
- Mention all 5 events.
- Mention locations naturally.
- Keep sentences short.
- Use phrases like:
  "Elsewhere"
  "Meanwhile"
  "If you're near"
  "Also worth checking out"
  "Later on"
  
Do not rewrite venue names or place names.

Preserve event titles exactly as supplied.

Preserve location names exactly as supplied.

Start EXACTLY with:

Here's what's happening today - {spoken_date}.

Events:

{event_list}

End EXACTLY with:

You can get all the latest events for where you are, from our website - visit tko dot radio for more!

Return only the script.
"""


response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents=prompt
)

script = response.text.strip()

# --------------------------------------------------
# Save script
# --------------------------------------------------

with open(
    "whatson.txt",
    "w",
    encoding="utf-8"
) as f:
    f.write(script)

print("\nSCRIPT\n")
print(script)

# --------------------------------------------------
# ElevenLabs
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
        "stability": 0.35,
        "similarity_boost": 0.75,
        "style": 0.45,
        "use_speaker_boost": True
    }
}

tts_response = requests.post(
    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
    headers=headers,
    json=payload,
    timeout=120
)

tts_response.raise_for_status()

with open("whatson.mp3", "wb") as f:
    f.write(tts_response.content)

print("MP3 generated successfully.")
