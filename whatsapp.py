import os
import uuid

import requests
from twilio.rest import Client

import config


def get_client():
    return Client(config.TWILIO_SID, config.TWILIO_TOKEN)


def send_message(to, body):
    """Send a text message via WhatsApp."""
    client = get_client()
    client.messages.create(
        from_=config.TWILIO_NUMBER,
        to=to,
        body=body,
    )


def send_image(to, image_url, caption=""):
    """Send an image via WhatsApp. image_url must be publicly accessible."""
    client = get_client()
    client.messages.create(
        from_=config.TWILIO_NUMBER,
        to=to,
        body=caption,
        media_url=[image_url],
    )


def download_media(media_url, board_id):
    """Download a media file from Twilio and save it locally.

    Twilio media URLs require authentication, so we use the account credentials.
    Returns the local file path.
    """
    board_dir = os.path.join(config.IMAGES_DIR, str(board_id))
    os.makedirs(board_dir, exist_ok=True)

    response = requests.get(
        media_url,
        auth=(config.TWILIO_SID, config.TWILIO_TOKEN),
        timeout=30,
    )
    response.raise_for_status()

    # Determine extension from content type
    content_type = response.headers.get("Content-Type", "image/jpeg")
    ext = "jpg"
    if "png" in content_type:
        ext = "png"
    elif "gif" in content_type:
        ext = "gif"
    elif "webp" in content_type:
        ext = "webp"

    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(board_dir, filename)

    with open(filepath, "wb") as f:
        f.write(response.content)

    return filepath
