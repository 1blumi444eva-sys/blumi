# File: /postbot/compositor/captioner.py
"""
Caption generator – creates caption image overlay.
Uses theme presets from utils.config.
"""

from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from backend.bots.postbot.utils.config import load_theme
import asyncio

async def create_captions(tts_path: str, auto: bool = True):
    await asyncio.sleep(1)
    return ["/content/fake_caption_1.png"]


def create_caption_image(video_path: str, text: str, workdir: str, theme: str) -> str:
    """Create caption overlay image with themed style."""
    style = load_theme(theme)
    img_path = Path(workdir) / "caption.png"

    # Minimal visual: fixed size, theme background
    img = Image.new("RGB", (1280, 200), color=style["bg"])
    draw = ImageDraw.Draw(img)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_path, 40)
    w, h = draw.textsize(text, font=font)
    draw.text(((1280 - w) / 2, (200 - h) / 2), text, fill=style["color"], font=font)

    img.save(img_path)
    return str(img_path)
