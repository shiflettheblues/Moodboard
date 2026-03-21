#!/usr/bin/env python3
"""Polling-based Moodboard bot — no webhook or tunnel required.

This script polls the Twilio Messages API for new incoming WhatsApp
messages, processes them through the same command handler, and sends
replies via the Twilio API.

Usage:
    python poll.py
"""

import time
import sys
import os
from datetime import datetime, timezone

import requests
from twilio.rest import Client

import config
import commands

os.makedirs(config.IMAGES_DIR, exist_ok=True)

POLL_INTERVAL = 5  # seconds between polls


def get_client():
    return Client(
        config.TWILIO_API_KEY_SID,
        config.TWILIO_API_KEY_SECRET,
        config.TWILIO_ACCOUNT_SID,
    )


def upload_image(file_path):
    """Upload a local image to catbox.moe and return the public URL."""
    with open(file_path, "rb") as f:
        resp = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": ("collage.jpg", f, "image/jpeg")},
        )
    resp.raise_for_status()
    url = resp.text.strip()
    print(f"  Uploaded collage -> {url}")
    return url


def send_reply(client, to, reply):
    """Send a reply, handling text and image responses."""
    if "__IMAGE__" in reply:
        parts = reply.split("__IMAGE__")
        local_url = parts[1]
        caption = parts[2] if len(parts) > 2 else ""

        # The URL from commands.py points to a local server that isn't running.
        # Resolve to the actual file path and upload to a public host.
        # URL format: {BASE_URL}/media/{board_id}/collage.jpg
        try:
            path_part = local_url.split("/media/", 1)[1]  # e.g. "1/collage.jpg"
            local_path = os.path.join(config.IMAGES_DIR, path_part)
            public_url = upload_image(local_path)
        except Exception as e:
            print(f"  Upload failed: {e}")
            client.messages.create(
                from_=config.TWILIO_NUMBER,
                to=to,
                body="Sorry, couldn't upload the collage image. Try again!",
            )
            return

        client.messages.create(
            from_=config.TWILIO_NUMBER,
            to=to,
            body=caption,
            media_url=[public_url],
        )
    else:
        client.messages.create(
            from_=config.TWILIO_NUMBER,
            to=to,
            body=reply,
        )


def poll_loop():
    client = get_client()
    seen_sids = set()
    # Process messages received in the last 5 minutes (catch msgs from downtime)
    from datetime import timedelta
    start_time = datetime.now(timezone.utc) - timedelta(minutes=5)

    print(f"Moodboard bot started (polling mode)")
    print(f"Watching for messages to {config.TWILIO_NUMBER}")
    print(f"Allowed numbers: {config.ALLOWED_NUMBERS or 'all'}")
    print(f"Polling every {POLL_INTERVAL}s — press Ctrl+C to stop\n")

    while True:
        try:
            messages = client.messages.list(
                to=config.TWILIO_NUMBER,
                date_sent_after=start_time,
                limit=20,
            )

            for msg in reversed(messages):  # oldest first
                if msg.sid in seen_sids:
                    continue
                seen_sids.add(msg.sid)

                phone = msg.from_
                body = msg.body or ""
                num_media = msg.num_media or "0"
                num_media = int(num_media)

                # Check allowed numbers
                if config.ALLOWED_NUMBERS and phone not in config.ALLOWED_NUMBERS:
                    print(f"  Ignored message from {phone} (not allowed)")
                    continue

                # Get media info if present
                media_url = ""
                media_type = ""
                if num_media > 0:
                    try:
                        media_list = msg.media.list()
                        if media_list:
                            m = media_list[0]
                            media_url = f"https://api.twilio.com{m.uri.replace('.json', '')}"
                            media_type = m.content_type or ""
                    except Exception as e:
                        print(f"  Warning: couldn't fetch media: {e}")

                print(f">> [{phone}] {body[:80]}" + (f" +{num_media} media" if num_media else ""))

                # Process through command handler
                reply = commands.handle_message(phone, body, num_media, media_url, media_type)
                send_reply(client, phone, reply)
                print(f"<< {reply[:100]}")

        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"Error during poll: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        poll_loop()
    except KeyboardInterrupt:
        print("\nBot stopped.")
