import subprocess
import shutil
from pathlib import Path
import pytest

from backend.bots.postbot.compositor.composer import merge_caption


def has_ffmpeg():
    return shutil.which("ffmpeg") is not None


@pytest.mark.skipif(not has_ffmpeg(), reason="ffmpeg not available")
def test_merge_caption_creates_output(tmp_path):
    # create a tiny background video (2s, 640x360)
    bg = tmp_path / "bg.mp4"
    caption = tmp_path / "caption.png"
    out = tmp_path / "out.mp4"

    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=black:s=640x360:d=2", str(bg)
    ], check=True, capture_output=True)

    # create a simple caption PNG via Pillow if available, otherwise skip
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        pytest.skip("Pillow not available to draw caption PNG")

    img = Image.new("RGBA", (640, 120), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    try:
        f = ImageFont.load_default()
    except Exception:
        f = None
    draw.text((10, 10), "Test Caption", fill=(255, 255, 255, 255), font=f)
    img.save(caption)

    # run merge_caption and assert result file exists
    merge_caption(str(bg), str(caption), str(out), fade_in=0.2, fade_out=0.2, duration=2.0)

    assert out.exists() and out.stat().st_size > 0
