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
    [e["title"] for e in 
