import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

import config

# Canvas dimensions (Instagram portrait ratio)
CANVAS_W = 1080
CANVAS_H = 1350
MARGIN = 20
TITLE_HEIGHT = 80
BG_COLOR = "#F5F0EB"
TITLE_BG = "#2C2C2C"
TITLE_COLOR = "#FFFFFF"
TEXT_BG_COLORS = ["#E8D5B7", "#B7D5E8", "#D5E8B7", "#E8B7D5", "#B7E8D5", "#D5B7E8"]
TEXT_COLOR = "#2C2C2C"
MAX_ITEMS = 12


def _get_font(size):
    """Try to load a nice font, fall back to default."""
    font_paths = [
        os.path.join(os.path.dirname(__file__), "fonts", "Montserrat-Bold.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def generate_collage(board_id, board_name, items):
    """Generate a mood board collage image from board items.

    Returns the file path to the generated collage.
    """
    image_items = [i for i in items if i.get("image_path") and os.path.exists(i["image_path"])]
    text_items = [i for i in items if i["item_type"] == "text"]

    # Limit items to avoid huge collages
    image_items = image_items[-MAX_ITEMS:]
    text_items = text_items[-6:]  # Cap text items

    total_visual = len(image_items) + len(text_items)
    if total_visual == 0:
        # Create an empty board placeholder
        canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), BG_COLOR)
        draw = ImageDraw.Draw(canvas)
        font = _get_font(32)
        draw.text((CANVAS_W // 2, CANVAS_H // 2), "No items yet!", fill=TEXT_COLOR, font=font, anchor="mm")
        return _save(canvas, board_id)

    # Determine grid layout
    cols = 2 if total_visual <= 4 else 3
    cell_w = (CANVAS_W - MARGIN * (cols + 1)) // cols

    # Calculate needed height
    rows_needed = (total_visual + cols - 1) // cols
    estimated_h = TITLE_HEIGHT + MARGIN + rows_needed * (cell_w + MARGIN) + MARGIN
    canvas_h = max(CANVAS_H, estimated_h)

    canvas = Image.new("RGB", (CANVAS_W, canvas_h), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # Draw title bar
    draw.rectangle([0, 0, CANVAS_W, TITLE_HEIGHT], fill=TITLE_BG)
    title_font = _get_font(36)
    draw.text((CANVAS_W // 2, TITLE_HEIGHT // 2), board_name.upper(), fill=TITLE_COLOR, font=title_font, anchor="mm")

    # Place items in grid
    x = MARGIN
    y = TITLE_HEIGHT + MARGIN
    row_max_h = 0
    color_idx = 0

    # Interleave images and text for visual variety
    all_visual = []
    img_iter = iter(image_items)
    txt_iter = iter(text_items)
    img_done = False
    txt_done = False

    # Alternate: 2 images, then 1 text
    while not (img_done and txt_done):
        for _ in range(2):
            try:
                all_visual.append(("image", next(img_iter)))
            except StopIteration:
                img_done = True
        try:
            all_visual.append(("text", next(txt_iter)))
        except StopIteration:
            txt_done = True

    # Add any remaining
    for item in img_iter:
        all_visual.append(("image", item))
    for item in txt_iter:
        all_visual.append(("text", item))

    for kind, item in all_visual:
        if x + cell_w > CANVAS_W:
            x = MARGIN
            y += row_max_h + MARGIN
            row_max_h = 0

        if kind == "image":
            cell_h = _place_image(canvas, item["image_path"], x, y, cell_w)
        else:
            cell_h = _place_text(canvas, draw, item["content"], x, y, cell_w, TEXT_BG_COLORS[color_idx % len(TEXT_BG_COLORS)])
            color_idx += 1

        row_max_h = max(row_max_h, cell_h)
        x += cell_w + MARGIN

    # Crop canvas to actual content
    final_h = y + row_max_h + MARGIN
    if final_h < canvas_h:
        canvas = canvas.crop((0, 0, CANVAS_W, final_h))

    return _save(canvas, board_id)


def _place_image(canvas, image_path, x, y, cell_w):
    """Place an image on the canvas, fitting it within the cell width. Returns the height used."""
    try:
        img = Image.open(image_path)
        img = img.convert("RGB")

        # Resize to fit cell width, maintaining aspect ratio
        ratio = cell_w / img.width
        new_h = int(img.height * ratio)
        # Cap height to prevent super tall images
        max_h = cell_w * 1.5
        if new_h > max_h:
            new_h = int(max_h)
            ratio = new_h / img.height
            new_w = int(img.width * ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            # Center crop to cell width
            left = (new_w - cell_w) // 2
            img = img.crop((left, 0, left + cell_w, new_h))
        else:
            img = img.resize((cell_w, new_h), Image.LANCZOS)

        canvas.paste(img, (x, y))
        return new_h
    except Exception:
        return cell_w  # Fallback height


def _place_text(canvas, draw, text, x, y, cell_w, bg_color):
    """Place a text block on the canvas. Returns the height used."""
    font = _get_font(24)
    padding = 20
    text_w = cell_w - padding * 2

    # Wrap text to fit
    wrapped = textwrap.fill(text, width=max(text_w // 12, 10))
    lines = wrapped.split("\n")

    # Calculate height
    line_height = 32
    text_h = len(lines) * line_height + padding * 2
    block_h = max(text_h, 100)  # Minimum height

    # Draw background rectangle with rounded feel
    draw.rectangle([x, y, x + cell_w, y + block_h], fill=bg_color)

    # Draw text
    text_y = y + padding
    for line in lines:
        draw.text((x + padding, text_y), line, fill=TEXT_COLOR, font=font)
        text_y += line_height

    return block_h


def _save(canvas, board_id):
    """Save the collage to disk and return the file path."""
    board_dir = os.path.join(config.IMAGES_DIR, str(board_id))
    os.makedirs(board_dir, exist_ok=True)
    out_path = os.path.join(board_dir, "collage.jpg")
    canvas.save(out_path, "JPEG", quality=90)
    return out_path
