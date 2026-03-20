import os

from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse

import config
import commands

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle incoming WhatsApp messages from Twilio."""
    phone = request.form.get("From", "")
    body = request.form.get("Body", "")
    num_media = int(request.form.get("NumMedia", 0))
    media_url = request.form.get("MediaUrl0", "")
    media_type = request.form.get("MediaContentType0", "")

    # Only respond to allowed numbers
    if config.ALLOWED_NUMBERS and phone not in config.ALLOWED_NUMBERS:
        return "", 200

    # Process the message
    reply = commands.handle_message(phone, body, num_media, media_url, media_type)

    # Check if reply contains an image to send
    if "__IMAGE__" in reply:
        parts = reply.split("__IMAGE__")
        image_url = parts[1]
        caption = parts[2] if len(parts) > 2 else ""
        resp = MessagingResponse()
        msg = resp.message(caption)
        msg.media(image_url)
        return str(resp), 200

    # Normal text reply
    resp = MessagingResponse()
    resp.message(reply)
    return str(resp), 200


@app.route("/media/<int:board_id>/<filename>")
def serve_media(board_id, filename):
    """Serve generated collage images so Twilio can fetch them."""
    directory = os.path.join(config.IMAGES_DIR, str(board_id))
    return send_from_directory(directory, filename)


@app.route("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}, 200


if __name__ == "__main__":
    # Ensure data directories exist
    os.makedirs(config.IMAGES_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
