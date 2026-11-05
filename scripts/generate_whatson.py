import os
import json
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import google.generativeai as genai

EVENT_URL = "https://pro.tko.radio/presenter-daily/event-source/"

# Tomorrow's date

tomorrow = datetime.now() + timedelta(days=1)

date_string = tomorrow.strftime("%A %d %B %Y")

# Download page

response = requests.get(EVENT_URL, timeout=30)

print("STATUS:", response.status_code)

with open("debug.html", "w", encoding="utf-8") as f:
    f.write(response.text)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

events = []

#
# YOU WILL PROBABLY NEED TO CHANGE THIS
# AFTER INSPECTING debug.html
#

for item in soup.select(".event-item"):
    text = item.get_text(" ", strip=True)

    if text:
        events.append(text)

events = list(dict.fromkeys(events))

print(f"Events found: {len(events)}")

if not events:
    raise Exception(
        "No events found. Check debug.html and update CSS selector."
    )

# Load event history

try:
    with open("used_events.json", "r") as f:
        history = json.load(f)
except:
    history = []

available = [e for e in events if e not in history]

if len(available) < 5:
    available = events

selected = random.sample(
    available,
    min(5, len(available))
)

history.extend(selected)

history = history[-35:]

with open("used_events.json", "w") as f:
    json.dump(history, f, indent=2)

# Gemini

genai.configure(
    api_key=os.environ["GEMINI_API_KEY"]
)

model = genai.GenerativeModel("gemini-1.5-flash")

event_list = "\n".join(
    [f"- {event}" for event in selected]
)

prompt = f"""
You are a Costa Blanca local radio presenter.

Create a short and natural sounding radio bulletin.

Requirements:

- Around 45 seconds.
- Mention all five events.
- Use a friendly local radio tone.
- Approximately 100 words.

Start EXACTLY with:

Here's what's happening today - {date_string}.

Events:

{event_list}

Finish EXACTLY with:

You can get all the latest events for where you are, from our website - visit tko dot radio for more!
"""

result = model.generate_content(prompt)

script = result.text.strip()

with open("whatson.txt", "w", encoding="utf-8") as f:
    f.write(script)

print(script)

# ElevenLabs

voice_id = os.environ["ELEVENLABS_VOICE_ID"]

headers = {
    "xi-api-key": os.environ["ELEVENLABS_API_KEY"],
    "Content-Type": "application/json"
}

payload = {
    "text": script,
    "model_id": "eleven_multilingual_v2"
}

r = requests.post(
    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
    headers=headers,
    json=payload,
    timeout=60
)

r.raise_for_status()

with open("whatson.mp3", "wb") as f:
    f.write(r.content)

print("MP3 created successfully")
