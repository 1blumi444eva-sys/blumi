import subprocess
from pathlib import Path
from backend.bots.postbot.utils.logger import get_logger

logger = get_logger("composer")

def merge_caption(
    video_path: str,
    caption_path: str,
    out_path: str,
    fade_in: float = 0.5,
    fade_out: float = 0.5,
    duration: float | None = None,
    y_offset_ratio: float = 0.85
) -> str:
    """
    Merge a static caption image onto a video with smooth fade-in/out transitions.

    Args:
        video_path: Path to the background video (input)
        caption_path: Caption image (usually .png with transparency)
        out_path: Final exported video file path
        fade_in: Seconds to fade in
        fade_out: Seconds to fade out
        duration: Optional explicit total duration (defaults to video length)
        y_offset_ratio: Vertical position of caption (0.0 = top, 1.0 = bottom)
    """
    try:
        logger.info(f"🎨 Merging caption → fade_in={fade_in}, fade_out={fade_out}, dur={duration}")

        # Build fade filters
        fade_filter = (
            f"[2:v]format=rgba,"
            f"fade=t=in:st=0:d={fade_in}:alpha=1,"
            f"fade=t=out:st={(duration - fade_out) if duration else 'end'}:d={fade_out}:alpha=1[cap];"
            f"[0:v][cap]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)*{y_offset_ratio}:format=auto[v]"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-i", str(caption_path),
            "-filter_complex", fade_filter,
            "-map", "[v]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            str(out_path)
        ]

        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"❌ FFmpeg merge_caption failed: {result.stderr}")
            raise RuntimeError("merge_caption ffmpeg failed")

        logger.info(f"✅ Caption merged successfully → {out_path}")
        return str(out_path)

    except Exception as e:
        logger.error(f"💥 merge_caption error: {e}")
        raise
