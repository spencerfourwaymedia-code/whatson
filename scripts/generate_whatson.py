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

        print(
            f"Pronunciation file error: {e}"
        )

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

    title 
