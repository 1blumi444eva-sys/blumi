# bots/postbot/compositor/captioner_async.py
import os
import math
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import aiofiles
import tempfile

def _load_font(font_name: str = "Arial", size: int = 64):
    try:
        return ImageFont.truetype(font_name, size)
    except Exception:
        # Fallback to default PIL bitmap
        return ImageFont.load_default()

def sample_frames_for_layout(video_path: str, sample_count: int = 3):
    """
    Extract N frames into a tempdir and return file paths.
    Simple, uses ffmpeg to get frames at equal intervals.
    """
    tmp = Path(tempfile.mkdtemp(prefix="cap_frames_"))
    # get duration
    cmd = ["ffprobe", "-v", "error", "-show_entries",
           "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    try:
        duration = float(proc.stdout.strip())
    except Exception:
        duration = 5.0
    times = [max(0, duration * (i + 0.5) / sample_count) for i in range(sample_count)]
    out_files = []
    for i, t in enumerate(times):
        out = tmp / f"frame_{i}.jpg"
        cmd = ["ffmpeg", "-y", "-ss", str(t), "-i", video_path, "-frames:v", "1", str(out)]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if out.exists():
            out_files.append(str(out))
    return out_files, duration

def pick_caption_region(frame_paths, grid=(3,3)):
    """
    Heuristic: compute edge density per grid cell across sampled frames; choose cell with lowest edges.
    Returns (x,y,w,h) relative to full frame.
    """
    if not frame_paths:
        return None
    accum_scores = None
    for fpath in frame_paths:
        im = Image.open(fpath).convert("L").filter(ImageFilter.FIND_EDGES)
        arr = np.array(im) / 255.0
        h, w = arr.shape
        rows, cols = grid
        cell_h = h // rows
        cell_w = w // cols
        scores = []
        for r in range(rows):
            for c in range(cols):
                sub = arr[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
                scores.append(sub.mean())
        scores = np.array(scores)
        if accum_scores is None:
            accum_scores = scores
        else:
            accum_scores += scores
    avg = accum_scores / max(1, len(frame_paths))
    idx = int(np.argmin(avg))
    rows, cols = grid
    r = idx // cols
    c = idx % cols
    return (c*cell_w, r*cell_h, cell_w, cell_h)

def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    cur = []
    for w in words:
        cur.append(w)
        if draw.textlength(" ".join(cur), font=font) > max_width:
            cur.pop()
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return "\n".join(lines)

def create_caption_image(video_path: str, narration: str, workdir: str, theme: str = "auto", font_name: str = "Arial"):
    """
    Smart caption image + fade timing.
    Produces: caption.png and caption_meta.json containing fade durations and placement.
    """
    frame_files, duration = sample_frames_for_layout(video_path, sample_count=3)
    region = pick_caption_region(frame_files, grid=(3,3))
    # defaults
    # If region is None, put at bottom-center
    tmpdir = Path(workdir)
    tmpdir.mkdir(parents=True, exist_ok=True)
    cap_img_path = tmpdir / "caption.png"
    meta_path = tmpdir / "caption_meta.json"

    # load the first frame to get resolution
    if frame_files:
        base = Image.open(frame_files[0])
        width, height = base.size
    else:
        width, height = 1280, 720

    # choose placement
    if not region:
        # bottom center
        box_w = int(width * 0.9)
        x = (width - box_w) // 2
        y = int(height * 0.78)
        box_h = int(height * 0.15)
    else:
        x, y, box_w, box_h = region
        # shrink a little
        box_w = int(box_w * 0.9)
        box_h = int(box_h * 0.6)
        x += int((region[2] - box_w) / 2)
        y += int((region[3] - box_h) / 2)

    # generate background gradient color based on theme
    theme_map = {
        "calm": ((20, 35, 80, 180), (60, 120, 200, 140)),
        "energetic": ((210, 110, 10, 180), (255, 190, 60, 140)),
        "mystery": ((30, 0, 60, 180), (70, 30, 120, 140)),
        "auto": ((0,0,0,160),(255,255,255,0))
    }
    c1, c2 = theme_map.get(theme, theme_map["auto"])

    # build caption image
    img = Image.new("RGBA", (width, height), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    # gradient rectangle
    rect = Image.new("RGBA", (box_w, box_h), (0,0,0,0))
    rdraw = ImageDraw.Draw(rect)
    # simple linear blend
    for i in range(box_h):
        t = i / max(1, box_h-1)
        r = int(c1[0] * (1-t) + c2[0] * t)
        g = int(c1[1] * (1-t) + c2[1] * t)
        b = int(c1[2] * (1-t) + c2[2] * t)
        a = int(c1[3] * (1-t) + c2[3] * t)
        rdraw.line([(0,i),(box_w,i)], fill=(r,g,b,a))
    img.paste(rect, (x, y), rect)

    # caption text (wrap)
    font = _load_font(font_name, size=int(box_h*0.42))
    # fallback for PIL versions lacking textlength/textbbox is handled by font.getsize
    try:
        lines = wrap_text(draw, narration.strip(), font, box_w - 20)
    except Exception:
        lines = narration.strip()

    # center-left inside box
    draw.multiline_text((x+10, y + 10), lines, font=font, fill=(255,255,255,255), spacing=4)
    img.save(cap_img_path)

    # metadata for fade timings
    fade_in = 0.5
    fade_out = 0.5
    # place fade_out start at duration - fade_out (safety)
    meta = {
        "caption_path": str(cap_img_path),
        "placement": {"x": x, "y": y, "w": box_w, "h": box_h},
        "duration": duration,
        "fade_in": fade_in,
        "fade_out": fade_out,
    }
    Path(meta_path).write_text(json.dumps(meta, indent=2))
    return str(cap_img_path)
