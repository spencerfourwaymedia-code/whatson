import os
import json
import random
import requests

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from google import genai

EVENT_URL = "https://pro.tko.radio/presenter-daily/event-source/"


# --------------------------------------------------
# Pronunciations
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

            if original in text:

                print(
                    f"Pronunciation: {original} -> {replacement}"
                )

                text = text.replace(
                    original,
                    replacement
                )

    except Exception as e:

        print(
            f"Pronunciation file error: {e}"
        )

    return text


# --------------------------------------------------
# Cleanup
# --------------------------------------------------

def cleanup_script(text):

    text = text.replace("*", "")
    text = text.replace("..", ".")
    text = text.replace("  ", " ")

    return text.strip()


# --------------------------------------------------
# Dropbox Access Token
# --------------------------------------------------

def get_dropbox_access_token():

    response = requests.post(
        "https://api.dropboxapi.com/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token":
                os.environ["DROPBOX_REFRESH_TOKEN"],
            "client_id":
                os.environ["DROPBOX_APP_KEY"],
            "client_secret":
                os.environ["DROPBOX_APP_SECRET"]
        },
        timeout=30
    )

    response.raise_for_status()

    return response.json()["access_token"]


# --------------------------------------------------
# Download Event Page
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
# Extract Events
# --------------------------------------------------

events = []

for item in soup.select("li.tko-event-item"):

    title_tag = item.select_one("strong")
    location_tag = item.select_one(".tko-event-location")
    date_tag = item.select_one(".tko-event-date")
    excerpt_tag = item.select_one(".tko-event-excerpt")

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

    excerpt = (
        excerpt_tag.get_text(
            " ",
            strip=True
        )
        if excerpt_tag
        else ""
    )

    if title:

        events.append(
            {
                "title": title,
                "location": location,
                "time": event_time,
                "excerpt": excerpt
            }
        )

print(
    f"Events found: {len(events)}"
)

if len(events) < 5:

    raise Exception(
        f"Only {len(events)} events found."
    )

# --------------------------------------------------
# Load History
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
    e for e in events
    if e["title"] not in history
]

if len(available) < 5:
    available = events

selected = random.sample(
    available,
    5
)

print(
    f"Selected {len(selected)} events"
)

history.extend(
    [e["title"] for e in selected]
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
# Spoken Date
# --------------------------------------------------

tomorrow = (
    datetime.now()
    + timedelta(days=1)
)

day = tomorrow.day

if 11 <= day <= 13:
    suffix = "th"
else:
    suffix = {
        1: "st",
        2: "nd",
        3: "rd"
    }.get(day % 10, "th")

spoken_day = (
    f"{tomorrow.strftime('%A')}, "
    f"the {day}{suffix} of "
    f"{tomorrow.strftime('%B')}"
)

# --------------------------------------------------
# Prompt Template
# --------------------------------------------------

with open(
    "whatson-prompt.txt",
    "r",
    encoding="utf-8"
) as f:

    template = f.read()

# --------------------------------------------------
# Event List
# --------------------------------------------------

event_list = ""

for event in selected:

    event_list += f"""
Title: {event['title']}
Location: {event['location']}
Time: {event['time']}
Description: {event['excerpt']}

"""

# --------------------------------------------------
# Gemini
# --------------------------------------------------

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)

prompt = f"""
{template}

DAY

{spoken_day}

EVENTS

{event_list}

OPEN EXACTLY WITH:

Here's what's happening on {spoken_day}.

CLOSE EXACTLY WITH:

You can get all the latest events for where you are, from our website - visit tko dot radio for more!

Return only the finished radio script.
"""

try:

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )

    script = response.text.strip()

except Exception as e:

    print(
        f"Gemini failure: {e}"
    )

    script = (
        f"Here's what's happening on {spoken_day}. "
    )

    for event in selected:

        script += (
            f"{event['title']} "
            f"at {event['location']}. "
        )

    script += (
        "You can get all the latest events for where you are, "
        "from our website - visit tko dot radio for more!"
    )

# --------------------------------------------------
# Process Script
# --------------------------------------------------

script = cleanup_script(
    script
)

script = apply_pronunciations(
    script
)

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

voice_id = os.environ[
    "ELEVENLABS_VOICE_ID"
]

headers = {
    "xi-api-key":
        os.environ[
            "ELEVENLABS_API_KEY"
        ],
    "Content-Type":
        "application/json"
}

payload = {
    "text": script,
    "model_id":
        "eleven_multilingual_v2",
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

    f.write(
        tts_response.content
    )

print(
    "MP3 generated successfully."
)

# --------------------------------------------------
# Dropbox Upload
# --------------------------------------------------

dropbox_token = (
    get_dropbox_access_token()
)

headers = {
    "Authorization":
        f"Bearer {dropbox_token}",
    "Dropbox-API-Arg":
        json.dumps({
            "path":
                "/Radio/WhatsOn/whatson_latest.mp3",
            "mode":
                "overwrite",
            "autorename":
                False
        }),
    "Content-Type":
        "application/octet-stream"
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
    "Dropbox upload successful."
)
