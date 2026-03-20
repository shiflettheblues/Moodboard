# Moodboard Agent — MEMORY.md

## What This Is
A WhatsApp bot for collecting images, text ideas, and Instagram posts, then generating a visual mood board collage. Built for personal use by a couple — send anything to the bot and it builds a mood board for you.

## Architecture
```
WhatsApp (you/wife) → Twilio → Flask webhook (app.py) → commands.py → storage/collage
                    ← Twilio ← Flask serves collage image ←
```

- **app.py** — Flask app with POST /webhook (receives messages) and GET /media/ (serves collages)
- **commands.py** — Parses incoming messages, dispatches to the right handler
- **storage.py** — SQLite database at data/moodboard.db, manages boards and items
- **whatsapp.py** — Twilio helpers for sending messages/images and downloading media
- **instagram.py** — Extracts images from Instagram post URLs (og:image scraping + instaloader fallback)
- **collage.py** — Pillow-based collage generator, creates 1080x1350 mood board images
- **config.py** — Loads environment variables from .env

## Key Commands
| Send this | What happens |
|---|---|
| `new board Kitchen Reno` | Creates a new board, makes it active |
| `show board` or `generate` | Generates the collage and sends it back |
| `status` | Shows board name, item count, breakdown |
| `list boards` | Lists all boards with item counts |
| `switch to <name>` | Changes the active board |
| `delete last` | Removes the most recently added item |
| `clear board` | Removes all items from active board |
| `help` | Shows command list |
| *(send an image)* | Adds it to the active board |
| *(send text)* | Adds as a text idea |
| *(send Instagram URL)* | Extracts image and adds it |

## Database Schema
- **boards**: id, name, created_by, created_at, is_active
- **items**: id, board_id, added_by, item_type (image/text/instagram), content, image_path, added_at
- Only one board is active at a time
- If no board exists when you send something, one is auto-created with today's date

## File Storage
- Images saved to `data/images/{board_id}/`
- Collages saved as `data/images/{board_id}/collage.jpg`
- The `data/` directory is gitignored

## Environment Variables (.env)
```
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_API_KEY_SID=SKxxxxx
TWILIO_API_KEY_SECRET=xxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
BASE_URL=https://your-ngrok-url.ngrok.io
ALLOWED_NUMBERS=whatsapp:+1XXXXXXXXXX,whatsapp:+1XXXXXXXXXX
```

## How to Run
1. Copy `.env.example` to `.env` and fill in your Twilio credentials
2. Install deps: `pip install -r requirements.txt`
3. Run: `python app.py`
4. Expose with ngrok: `ngrok http 5000`
5. Set the ngrok URL as your Twilio WhatsApp sandbox webhook (POST to /webhook)
6. Both users join the Twilio sandbox by sending the join code from WhatsApp

## Twilio WhatsApp Sandbox Setup
1. Go to https://console.twilio.com → Messaging → Try WhatsApp
2. Note the sandbox join code (e.g., "join word-word")
3. Send that code from both phones to the Twilio sandbox number
4. Set webhook URL to: `{your_ngrok_url}/webhook` (HTTP POST)
5. Sandbox sessions expire after 72 hours of inactivity — re-join if needed

## Known Quirks
- **Instagram scraping is fragile.** Instagram changes their page structure regularly. If og:image extraction fails, instaloader is tried as fallback. If both fail, the link is saved but the user is told to send a screenshot instead.
- **Twilio sandbox expires.** After 72 hours of inactivity, you need to re-join. For permanent use, register a proper WhatsApp sender through Twilio (requires Meta Business verification).
- **ngrok URL changes on restart.** Either use ngrok's paid plan for a stable subdomain, or deploy to a VPS.
- **Collage caps at 12 images.** Shows the latest 12 to prevent huge/tiny outputs. Text items capped at 6.
- **Collage is synchronous.** Large boards may take a few seconds to generate.

## Deployment (Future)
For permanent hosting, deploy to any cheap VPS:
- DigitalOcean, Hetzner, Railway, Render, etc.
- Run with gunicorn: `gunicorn app:app -b 0.0.0.0:5000`
- Put behind nginx with HTTPS for the media serving endpoint
- Replace ngrok URL with your domain in .env

## Recent Changes
- Initial build: WhatsApp bot with image/text/Instagram collection and collage generation
