import os
import re
import uuid

import requests
from bs4 import BeautifulSoup

import config

SHORTCODE_RE = re.compile(r"instagram\.com/(?:p|reel|reels)/([A-Za-z0-9_-]+)")


def extract_shortcode(url):
    """Extract the shortcode from an Instagram URL."""
    match = SHORTCODE_RE.search(url)
    return match.group(1) if match else None


def extract_image_url(instagram_url):
    """Try to extract the main image URL from an Instagram post.

    Primary method: parse og:image meta tag from the page HTML.
    Fallback: use instaloader library.
    Returns the image URL string, or None if extraction fails.
    """
    # Method 1: og:image scraping
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(instagram_url, headers=headers, timeout=10)
        if resp.ok:
            soup = BeautifulSoup(resp.text, "html.parser")
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                return og_image["content"]
    except Exception:
        pass

    # Method 2: instaloader fallback
    shortcode = extract_shortcode(instagram_url)
    if shortcode:
        try:
            import instaloader

            loader = instaloader.Instaloader()
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            return post.url
        except Exception:
            pass

    return None


def download_instagram_image(instagram_url, board_id):
    """Download the image from an Instagram post and save locally.

    Returns (local_file_path, original_url) or (None, instagram_url) on failure.
    """
    image_url = extract_image_url(instagram_url)
    if not image_url:
        return None, instagram_url

    board_dir = os.path.join(config.IMAGES_DIR, str(board_id))
    os.makedirs(board_dir, exist_ok=True)

    try:
        resp = requests.get(image_url, timeout=15)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "image/jpeg")
        ext = "jpg"
        if "png" in content_type:
            ext = "png"
        elif "webp" in content_type:
            ext = "webp"

        filename = f"ig_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(board_dir, filename)

        with open(filepath, "wb") as f:
            f.write(resp.content)

        return filepath, instagram_url
    except Exception:
        return None, instagram_url
