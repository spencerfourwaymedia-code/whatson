import os
import re
import json
import random
import requests

from bs4 import BeautifulSoup
from datetime import datetime, timedelta

print("Starting script...", flush=True)

EVENT_URL = "https://pro.tko.radio/presenter-daily/event-source/"


# --------------------------------------------------
# Cleanup
# --------------------------------------------------

def cleanup_script(text):

    text = text.replace("*", "")
    text = text.replace("..", ".")
    text = text.replace("  ", " ")

    return text.strip()


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
                    f"Pronunciation: "
                    f"{original} -> {replacement}",
                    flush=True
                )

                text = text.replace(
                    original,
                    replacement
                )

    except Exception as e:

        print(
            f"Pronunciation file error: {e}",
            flush=True
        )

    return text


# --------------------------------------------------
# Excerpt Processing
# --------------------------------------------------

def radio_time(text):

    replacements = {
        "13:00": "one this afternoon",
        "14:00": "two this afternoon",
        "15:00": "three this afternoon",
        "16:00": "four this afternoon",
        "17:00": "five this afternoon",

        "17:30": "half past five this afternoon",
        "16:30": "half past four this afternoon",
        "15:30": "half past three this afternoon",

        "18:00": "six tonight",
        "19:00": "seven tonight",
        "20:00": "eight tonight",
        "21:00": "nine tonight",
        "22:00": "ten tonight",

        "18:15": "quarter past six tonight",
        "19:15": "quarter past seven tonight",
        "20:15": "quarter past eight tonight",

        "18:30": "half past six tonight",
        "19:30": "half past seven tonight",
        "20:30": "half past eight tonight",

        "18:45": "quarter to seven tonight",
        "19:45": "quarter to eight tonight",
        "20:45": "quarter to nine tonight"
    }

    for original, spoken in replacements.items():

        text = text.replace(
            original,
            spoken
        )

    text = re.sub(
        r"\b8pm\b",
        "eight tonight",
        text,
        flags=re.I
    )

    text = re.sub(
        r"\b7pm\b",
        "seven tonight",
        text,
        flags=re.I
    )

    text = re.sub(
        r"\b6pm\b",
        "six tonight",
        text,
        flags=re.I
    )

    text = re.sub(
        r"\b5pm\b",
        "five this afternoon",
        text,
        flags=re.I
    )

    return text

def clean_excerpt(excerpt, title):

    if not excerpt:
        return ""

    excerpt = (
        excerpt
        .replace("\n", " ")
        .replace("\r", " ")
        .strip()
    )

    sentences = re.split(
        r'(?<=[.!?])\s+',
        excerpt
    )

    cleaned = []

    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue

        #
        # Only remove title repetition
        #

        if sentence.lower().startswith(
            title.lower()
        ):
            continue

        cleaned.append(
            sentence
        )

        #
        # Maximum two complete sentences
        #

        if len(cleaned) >= 2:
            break

    result = " ".join(cleaned)

    if (
        result
        and not result.endswith(
            (".", "!", "?")
        )
    ):
        result += "."

    result = radio_time(
        result
    )

    return result


# --------------------------------------------------
# Dropbox Access Token
# --------------------------------------------------

def get_dropbox_access_token():

    response = requests.post(
        "https://api.dropboxapi.com/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token":
                os.environ[
                    "DROPBOX_REFRESH_TOKEN"
                ],
            "client_id":
                os.environ[
                    "DROPBOX_APP_KEY"
                ],
            "client_secret":
                os.environ[
                    "DROPBOX_APP_SECRET"
                ]
        },
        timeout=30
    )

    if response.status_code != 200:

        raise Exception(
            response.text
        )

    return response.json()[
        "access_token"
    ]


# --------------------------------------------------
# Download Event Page
# --------------------------------------------------

response = requests.get(
    EVENT_URL,
    timeout=30
)

print(
    f"STATUS: {response.status_code}",
    flush=True
)

response.raise_for_status()

with open(
    "debug.html",
    "w",
    encoding="utf-8"
) as f:

    f.write(
        response.text
    )

soup = BeautifulSoup(
    response.text,
    "html.parser"
)

# --------------------------------------------------
# Extract Events
# --------------------------------------------------

events = []

for item in soup.select(
    "li.tko-event-item"
):

    title_tag = item.select_one(
        "strong"
    )

    location_tag = item.select_one(
        ".tko-event-location"
    )

    date_tag = item.select_one(
        ".tko-event-date"
    )

    excerpt_tag = item.select_one(
        ".tko-event-excerpt"
    )

    title = (
        title_tag.get_text(
            strip=True
        )
        if title_tag
        else ""
    )

    location = (
        location_tag.get_text(
            " ",
            strip=True
        )
        .replace(
            "Location:",
            ""
        )
        .strip()
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
    f"Events found: {len(events)}",
    flush=True
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
    f"Selected {len(selected)} events",
    flush=True
)

history.extend(
    [
        e["title"]
        for e in selected
    ]
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
# Generate Script
# --------------------------------------------------

print(
    "Generating radio script...",
    flush=True
)

intro_phrases = [
    "If you're looking for something to do today,",
    "Getting things underway,",
    "First up,",
    "Starting the day off,"
]

middle_phrases = [
    "Elsewhere,",
    "Meanwhile,",
    "Also worth checking out,",
    "Over in another part of the Costa Blanca,"
]

ending_phrases = [
    "Later on,",
    "Looking ahead to the evening,",
    "And if you're still out and about,",
    "Rounding off the day's events,"
]

selected.sort(
    key=lambda x: x["time"]
)

script = (
    f"Here's what's happening on "
    f"{spoken_day}. "
)

for index, event in enumerate(
    selected
):

    title = event["title"]

    location = (
        event["location"]
        or "the Costa Blanca"
    )

    description = clean_excerpt(
        event["excerpt"],
        title
    )

    if index == 0:

        transition = random.choice(
            intro_phrases
        )

    elif index == len(selected) - 1:

        transition = random.choice(
            ending_phrases
        )

    else:

        transition = random.choice(
            middle_phrases
        )

    script += (
        f"{transition} "
        f"{title}"
    )

    if location:

        script += (
            f" at {location}. "
        )

    else:

        script += ". "

    if description:

        script += (
            f"{description} "
        )

script += (
    "You can get all the latest events "
    "for where you are, from our website "
    "- visit tko dot radio for more!"
)

# --------------------------------------------------
# Process Script
# --------------------------------------------------

script = cleanup_script(
    script
)

script = radio_time(
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

print(
    "\nSCRIPT\n",
    flush=True
)

print(
    script,
    flush=True
)

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
    "MP3 generated successfully.",
    flush=True
)

# --------------------------------------------------
# Dropbox Upload
# --------------------------------------------------

try:

    print(
        "Attempting Dropbox upload...",
        flush=True
    )

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

    if upload_response.status_code != 200:

        print(
            f"Dropbox upload failed: "
            f"{upload_response.text}",
            flush=True
        )

    else:

        print(
            "Dropbox upload successful.",
            flush=True
        )

except Exception as e:

    print(
        f"Dropbox upload skipped: {e}",
        flush=True
    )
