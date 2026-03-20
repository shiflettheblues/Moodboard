import os
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_API_KEY_SID = os.environ.get("TWILIO_API_KEY_SID", "")
TWILIO_API_KEY_SECRET = os.environ.get("TWILIO_API_KEY_SECRET", "")
TWILIO_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")
ALLOWED_NUMBERS = [
    n.strip() for n in os.environ.get("ALLOWED_NUMBERS", "").split(",") if n.strip()
]

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "moodboard.db")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
