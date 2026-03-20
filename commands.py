import re

import storage
import instagram
import whatsapp
import collage
import config

INSTAGRAM_RE = re.compile(r"https?://(?:www\.)?instagram\.com/(?:p|reel|reels)/[A-Za-z0-9_-]+")

HELP_TEXT = """*Moodboard Bot Commands:*

*new board <name>* — Create a new board
*show board* — Generate and send the collage
*status* — Current board info
*list boards* — Show all boards
*switch to <name>* — Switch active board
*delete last* — Remove last added item
*clear board* — Remove all items
*help* — Show this message

Or just send an image, text, or Instagram link to add it to your active board!"""


def parse_message(body, num_media, media_url, media_type):
    """Parse an incoming message and return its type and payload.

    Returns dict with keys: type, payload
    Types: command, instagram, image, text
    """
    body_stripped = (body or "").strip()
    body_lower = body_stripped.lower()

    # Check for explicit commands first
    if body_lower.startswith("new board "):
        return {"type": "command", "command": "new_board", "payload": body_stripped[10:].strip()}
    if body_lower in ("show board", "generate", "show", "make board"):
        return {"type": "command", "command": "show_board", "payload": None}
    if body_lower == "status":
        return {"type": "command", "command": "status", "payload": None}
    if body_lower in ("list boards", "list", "boards"):
        return {"type": "command", "command": "list_boards", "payload": None}
    if body_lower.startswith("switch to "):
        return {"type": "command", "command": "switch", "payload": body_stripped[10:].strip()}
    if body_lower == "delete last":
        return {"type": "command", "command": "delete_last", "payload": None}
    if body_lower == "clear board":
        return {"type": "command", "command": "clear_board", "payload": None}
    if body_lower == "help":
        return {"type": "command", "command": "help", "payload": None}

    # Check for Instagram URL
    ig_match = INSTAGRAM_RE.search(body_stripped)
    if ig_match:
        return {"type": "instagram", "payload": ig_match.group(0)}

    # Check for image attachment
    if num_media > 0 and media_url and (media_type or "").startswith("image/"):
        return {"type": "image", "payload": media_url, "caption": body_stripped}

    # Everything else is a text idea
    if body_stripped:
        return {"type": "text", "payload": body_stripped}

    return {"type": "unknown", "payload": None}


def handle_message(phone, body, num_media, media_url, media_type):
    """Process an incoming message and return a reply string."""
    parsed = parse_message(body, num_media, media_url, media_type)
    msg_type = parsed["type"]

    if msg_type == "command":
        return _handle_command(phone, parsed["command"], parsed["payload"])
    elif msg_type == "instagram":
        return _handle_instagram(phone, parsed["payload"])
    elif msg_type == "image":
        return _handle_image(phone, parsed["payload"], parsed.get("caption", ""))
    elif msg_type == "text":
        return _handle_text(phone, parsed["payload"])
    else:
        return "Hmm, not sure what to do with that. Send *help* for a list of commands."


def _handle_command(phone, command, payload):
    if command == "new_board":
        board = storage.create_new_board(phone, payload)
        return f"Created new board: *{board['name']}*"

    elif command == "show_board":
        board = storage.get_or_create_active_board(phone)
        items = storage.get_board_items(board["id"])
        if not items:
            return f"*{board['name']}* is empty. Send some images or ideas first!"

        image_items = [i for i in items if i.get("image_path")]
        text_items = [i for i in items if i["item_type"] == "text"]
        if not image_items and not text_items:
            return f"*{board['name']}* has no displayable items yet."

        collage_path = collage.generate_collage(board["id"], board["name"], items)
        # Return a special marker so app.py knows to send an image
        collage_url = f"{config.BASE_URL}/media/{board['id']}/collage.jpg"
        return f"__IMAGE__{collage_url}__IMAGE__Here's your mood board for *{board['name']}*!"

    elif command == "status":
        board = storage.get_or_create_active_board(phone)
        status = storage.get_board_status(board["id"])
        total = sum(status.values())
        breakdown = ", ".join(f"{count} {t}" for t, count in status.items()) if status else "nothing yet"
        return f"*{board['name']}*: {total} items ({breakdown})"

    elif command == "list_boards":
        boards = storage.list_boards()
        if not boards:
            return "No boards yet. Send something to create your first one!"
        lines = []
        for b in boards:
            active = " ← active" if b["is_active"] else ""
            lines.append(f"• *{b['name']}* ({b['item_count']} items){active}")
        return "Your boards:\n" + "\n".join(lines)

    elif command == "switch":
        board = storage.switch_board(payload)
        if board:
            return f"Switched to *{board['name']}*"
        return f"Couldn't find a board matching \"{payload}\""

    elif command == "delete_last":
        board = storage.get_or_create_active_board(phone)
        deleted = storage.delete_last_item(board["id"])
        if deleted:
            return f"Removed the last {deleted['item_type']} from *{board['name']}*"
        return "Nothing to delete — board is empty."

    elif command == "clear_board":
        board = storage.get_or_create_active_board(phone)
        count = storage.clear_board(board["id"])
        return f"Cleared {count} items from *{board['name']}*"

    elif command == "help":
        return HELP_TEXT

    return "Unknown command. Send *help* for a list of commands."


def _handle_instagram(phone, url):
    board = storage.get_or_create_active_board(phone)
    image_path, original_url = instagram.download_instagram_image(url, board["id"])

    if image_path:
        count = storage.add_item(board["id"], phone, "instagram", original_url, image_path)
        return f"Added Instagram post to *{board['name']}* ({count} items now)"
    else:
        # Couldn't extract — store the link anyway
        count = storage.add_item(board["id"], phone, "instagram", original_url, None)
        return (
            f"Saved the Instagram link to *{board['name']}* ({count} items now), "
            "but couldn't grab the image. Try sending a screenshot instead!"
        )


def _handle_image(phone, media_url, caption):
    board = storage.get_or_create_active_board(phone)
    image_path = whatsapp.download_media(media_url, board["id"])
    content = caption if caption else "image"
    count = storage.add_item(board["id"], phone, "image", content, image_path)
    return f"Added to *{board['name']}* ({count} items now)"


def _handle_text(phone, text):
    board = storage.get_or_create_active_board(phone)
    count = storage.add_item(board["id"], phone, "text", text, None)
    return f"Added \"{text}\" to *{board['name']}* ({count} items now)"
