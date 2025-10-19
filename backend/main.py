"""
PostBot v11 — Async Orchestrator Core (with Smart Captioner)
-------------------------------------------------------------
Coordinates narration, TTS, media fetch, caption, and composition.

Features:
 - Async parallelism for faster generation
 - Style-aware narration length fitting
 - Smart caption placement (edge density heuristic)
 - Safe OpenAI v1 client calls
 - ElevenLabs TTS
 - Fade-in/out caption blending
"""

from __future__ import annotations
import asyncio
import json
import tempfile
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any
from bots.postbot.generator.narrator import generate_narration
from bots.postbot.generator.tts_engine import synthesize_tts
from bots.postbot.generator.media_fetcher import fetch_video
from bots.postbot.compositor.captioner_async import create_caption_image
from bots.postbot.compositor.mixer import mix_audio_video
from bots.postbot.compositor.composer import merge_caption
from bots.postbot.utils.config import load_config
from bots.postbot.utils.logger import get_logger
from bots.postbot.utils.metadata import append_run
from bots.postbot.utils.paths import rotate_old_runs
# backend/main.py
import uvicorn
import os
from backend.api import create_app


logger = get_logger("postbot")

STYLE_TARGET_SECONDS = {
    "ad": 10,
    "post": 30,
    "story": 90,
}


# ---------- Async wrappers ----------
async def a_generate_narration(topic: str, theme: str, style: str) -> str:
    target_seconds = STYLE_TARGET_SECONDS.get(style, 30)
    return await asyncio.to_thread(generate_narration, topic, theme, style, target_seconds)


async def a_fetch_video(topic: str, out_path: str) -> str:
    return await asyncio.to_thread(fetch_video, topic, out_path)


async def a_synthesize_tts(text: str, out_path: str) -> str:
    return await asyncio.to_thread(synthesize_tts, text, out_path)


async def a_create_caption_image(video_path: str, narration: str, workdir: str, theme: str) -> str:
    return await asyncio.to_thread(create_caption_image, video_path, narration, workdir, theme)


async def a_mix_audio_video(video_path: str, audio_path: str, out_path: str) -> str:
    return await asyncio.to_thread(mix_audio_video, video_path, audio_path, out_path)


async def a_merge_caption(video_path: str, caption_path: str, out_path: str, fade_in: float = 0.5, fade_out: float = 0.5, duration: float | None = None) -> str:
    return await asyncio.to_thread(merge_caption, video_path, caption_path, out_path, fade_in, fade_out, duration)


# ---------- Orchestrator ----------
async def make_video(topic: str, style: str, theme: str, run_root: Path | None = None) -> Path:
    """Async orchestrator that builds a full PostBot short-form video."""
    cfg = load_config()
    timeout = cfg.get("timeout_seconds", 240)
    keep_runs = cfg.get("keep_runs", 20)
    workdir = Path(tempfile.mkdtemp(prefix="postbot_")) if run_root is None else run_root
    workdir.mkdir(parents=True, exist_ok=True)

    logger.info(f"🚀 Starting PostBot run for topic='{topic}' style='{style}' theme='{theme}' in {workdir}")

    bg_path = str(workdir / "bg.mp4")
    audio_path = str(workdir / "narration.mp3")
    merged_path = str(workdir / "merged.mp4")
    caption_path = str(workdir / "caption.png")
    final_path = workdir / "final.mp4"

    try:
        # --- 1️⃣ Narration + Video Fetch (parallel)
        narration_task = asyncio.create_task(a_generate_narration(topic, theme, style))
        video_task = asyncio.create_task(a_fetch_video(topic, bg_path))

        narration = await asyncio.wait_for(narration_task, timeout)
        logger.info(f"🧠 Narration ready ({len(narration)} chars)")

        # --- 2️⃣ TTS + Video Download
        tts_task = asyncio.create_task(a_synthesize_tts(narration, audio_path))
        video = await asyncio.wait_for(video_task, timeout)
        logger.info(f"🎬 Video fetched: {video}")

        audio_result = await asyncio.wait_for(tts_task, timeout)
        logger.info(f"🎤 TTS done: {audio_result}")

        # --- 3️⃣ Smart Caption
        caption_img = await asyncio.wait_for(a_create_caption_image(video, narration, str(workdir), theme), timeout)
        logger.info(f"💬 Caption generated: {caption_img}")

        # Load fade metadata if available
        meta_file = Path(workdir) / "caption_meta.json"
        fade_in = fade_out = 0.5
        duration = None
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text())
                fade_in = meta.get("fade_in", 0.5)
                fade_out = meta.get("fade_out", 0.5)
                duration = meta.get("duration")
            except Exception:
                pass

        # --- 4️⃣ Mix audio/video
        mixed = await asyncio.wait_for(a_mix_audio_video(video, audio_result, merged_path), timeout)
        logger.info(f"🎧 Mixed A/V: {mixed}")

        # --- 5️⃣ Merge caption
        final = await asyncio.wait_for(a_merge_caption(mixed, caption_img, str(final_path), fade_in, fade_out, duration), timeout)
        logger.info(f"✅ Final video: {final}")

        # --- 6️⃣ Metadata
        metadata_entry = {
            "run_id": workdir.name,
            "topic": topic,
            "style": style,
            "theme": theme,
            "video": str(final),
            "created_at": datetime.now(UTC).isoformat(),
        }
        append_run(metadata_entry)
        rotate_old_runs(Path(tempfile.gettempdir()), keep=keep_runs)

        return final

    except asyncio.TimeoutError:
        logger.error(f"⏰ Timeout during run: topic={topic}")
        raise
    except Exception as e:
        logger.error(f"💥 Run failed for {topic}: {e}")
        raise


def run_make_video(topic: str, style: str, theme: str) -> Path:
    """Sync wrapper for quick testing or CLI usage."""
    return asyncio.run(make_video(topic, style, theme))


if __name__ == "__main__":
    try:
        result = run_make_video("quantum computing", "post", "energetic")
        logger.info(f"🎉 Output video at {result}")
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
