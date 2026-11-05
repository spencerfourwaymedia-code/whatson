import os
import json
import random
import requests

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from google import genai

EVENT_URL = "https://pro.tko.radio/presenter-daily/event-source/"


# --------------------------------------------------
# Pronunciation handling
# --------------------------------------------------

def apply_pronunciations(text):
    try:
        with open(
            "pronunciations.json",
            "r",
            encoding="utf-8"
        ) as f:
            replacements = json.load(f)

        for original, replacement in replacements.items():
            text = text.replace(
                original,
                replacement
            )

    except Exception as e:
        print(f"Pronunciation file error: {e}")

    return text


# --------------------------------------------------
# Script cleanup
# --------------------------------------------------

def cleanup_script(text):

    text = text.replace("*", "")
    text = text.replace("..", ".")
    text = text.replace("  ", " ")

    return text.strip()


# --------------------------------------------------
# Download event page
# --------------------------------------------------

response = requests.get(
    EVENT_URL,
    timeout=30
)

print(f"STATUS: {response.status_code}")

with open(
    "debug.html",
    "w",
    encoding="utf-8"
) as f:
    f.write(response.text)

response.raise_for_status()

soup = BeautifulSoup(
    response.text,
    "html.parser"
)

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
        else ""
    )

    location = (
        location_tag.get_text(
            " ",
            strip=True
        ).replace(
            "Location:",
            ""
        ).strip()
        if location_tag
        else ""
    )

    event_time = (
        date_tag.get_text(
            " ",
            strip=True
        )
        if date_tag
        else ""
    )

    if title:
        events.append(
            {
                "title": title,
                "location": location,
                "time": event_time
            }
        )

print(f"Events found: {len(events)}")

if len(events) < 5:
    raise Exception(
        f"Expected at least 5 events but found {len(events)}"
    )

# --------------------------------------------------
# Load history
# --------------------------------------------------

try:

    with open(
        "used_events.json",
        "r",
        encoding="utf-8"
    ) as f:

        history = json.load(f)

except Exception:

    history = []

available = [
    event for event in events
    if event["title"] not in history
]

if len(available) < 5:
    available = events

selected = random.sample(
    available,
    5
)

# --------------------------------------------------
# Update history
# --------------------------------------------------

history.extend(
    [event["title"] for event in selected]
)

history = history[-50:]

with open(
    "used_events.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        history,
        f,
        indent=2
    )

# --------------------------------------------------
# Spoken day
# --------------------------------------------------

tomorrow = datetime.now() + timedelta(days=1)

spoken_day = tomorrow.strftime("%A")

# --------------------------------------------------
# Build Gemini Event List
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
You are writing a short local radio feature
for TKO Radio Spain.

This script will be voiced by an AI presenter.

Write for radio.

STYLE

- Friendly
- Warm
- Conversational
- Natural spoken English
- Human sounding
- Suitable for commercial radio

REQUIREMENTS

- Mention all 5 events.
- Preserve event titles exactly.
- Preserve location names exactly.
- Do not rewrite place names.
- Do not invent information.
- Do not sound like a list.
- Around 100 to 120 words.

Use transitions such as:

Meanwhile
Elsewhere
Later on
Also worth checking out
If you're near

OPEN EXACTLY WITH:

Here's what's happening on {spoken_day}.

EVENTS

{event_list}

CLOSE EXACTLY WITH:

You can get all the latest events for where you are, from our website - visit tko dot radio for more!

Return only the final script.
"""

# --------------------------------------------------
# Generate Script
# --------------------------------------------------

try:

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )

    script = response.text.strip()

except Exception as e:

    print(f"Gemini failure: {e}")

    script = (
        f"Here's what's happening on {spoken_day}. "
    )

    for event in selected:

        script += (
            f"{event['title']} at "
            f"{event['location']}. "
        )

    script += (
        "You can get all the latest events for where you are, "
        "from our website - visit tko dot radio for more!"
    )

# --------------------------------------------------
# Cleanup
# --------------------------------------------------

script = cleanup_script(script)

script = apply_pronunciations(script)

# --------------------------------------------------
# Save text file
# --------------------------------------------------

with open(
    "whatson.txt",
    "w",
    encoding="utf-8"
) as f:

    f.write(script)

print("\nSCRIPT:\n")
print(script)

# --------------------------------------------------
# ElevenLabs
# --------------------------------------------------

voice_id = os.environ[
    "ELEVENLABS_VOICE_ID"
]

headers = {
    "xi-api-key": os.environ[
        "ELEVENLABS_API_KEY"
    ],
    "Content-Type": "application/json"
}

payload = {
    "text": script,
    "model_id": "eleven_multilingual_v2",
    "voice_settings": {
        "stability": 0.28,
        "similarity_boost": 0.75,
        "style": 0.65,
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

with open(
    "whatson.mp3",
    "wb"
) as f:

    f.write(tts_response.content)

print("MP3 generated successfully.")

# --------------------------------------------------
# Upload to Dropbox
# --------------------------------------------------

dropbox_token = os.environ.get(
    "DROPBOX_ACCESS_TOKEN"
)

if dropbox_token:

    headers = {
        "Authorization": f"Bearer {dropbox_token}",
        "Dropbox-API-Arg": json.dumps({
            "path": "/Whatson/whatson_latest.mp3",
            "mode": "overwrite",
            "autorename": False,
            "mute": True
        }),
        "Content-Type": "application/octet-stream"
    }

    with open(
        "whatson.mp3",
        "rb"
    ) as f:

        upload_response = requests.post(
            "https://content.dropboxapi.com/2/files/upload",
            headers=headers,
            data=f.read(),
            timeout=120
        )

    upload_response.raise_for_status()

    print(
        "Dropbox upload successful: /Whatson/whatson_latest.mp3"
    )

else:

    print(
        "DROPBOX_ACCESS_TOKEN not configured"
    )
