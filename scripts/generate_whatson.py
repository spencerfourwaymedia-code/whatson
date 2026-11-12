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
# Dropbox
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
# History
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

selected
