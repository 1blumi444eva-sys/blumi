import os
import subprocess
import shlex
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

        # Build fade filters. Caption is provided as the second input (-i caption_path)
        # so its input index is 1 (0 is the background video). Only add the
        # fade-out if we know the duration; otherwise just fade in.
        if duration is not None:
            fade_out_start = max(0, float(duration) - float(fade_out))
            fade_filter = (
                f"[1:v]format=rgba,"
                f"fade=t=in:st=0:d={fade_in}:alpha=1,"
                f"fade=t=out:st={fade_out_start}:d={fade_out}:alpha=1[cap];"
                f"[0:v][cap]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)*{y_offset_ratio}:format=auto[v]"
            )
        else:
            fade_filter = (
                f"[1:v]format=rgba,"
                f"fade=t=in:st=0:d={fade_in}:alpha=1[cap];"
                f"[0:v][cap]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)*{y_offset_ratio}:format=auto[v]"
            )

        # Force social-media friendly specs: 1080x1920 (portrait), 30fps, AAC audio
        # Ensure the final filter graph produces a named video label ([vfinal])
        # that can be mapped safely by ffmpeg. The overlay step produces [v],
        # so scale from [v] and emit [vfinal]. If the overlay already emitted
        # a different label, this still consumes [v] and writes [vfinal].
        scale_filter = (
            f"[v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black[vfinal]"
        )
        vf = f"{fade_filter};{scale_filter}" if fade_filter else scale_filter

        # Log the resolved filter_complex for easier debugging
        logger.info("FFmpeg filter_complex: %s", vf)

        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-i", str(caption_path),
            "-filter_complex", vf,
            "-map", "[vfinal]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-r", "30",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            str(out_path)
        ]

        logger.info("Running ffmpeg merge command: %s", " ".join(cmd))

        # Optionally dump the filter graph and command to a debug file next to
        # the output so CI and local runs can inspect the exact ffmpeg inputs.
        try:
            dump = False
            if os.environ.get("BLUMI_DUMP_FILTER"):
                dump = True
            # always dump in test runs (pytest sets PYTEST_CURRENT_TEST sometimes),
            # but guard to avoid noisy disks in production by default.
            if os.environ.get("PYTEST_CURRENT_TEST"):
                dump = True
            if dump:
                debug_path = Path(out_path).with_suffix("")
                debug_file = debug_path.with_name(debug_path.name + "_ffmpeg_debug.txt")
                try:
                    with open(debug_file, "w", encoding="utf-8") as df:
                        df.write("FILTER_COMPLEX:\n")
                        df.write(vf + "\n\n")
                        df.write("COMMAND:\n")
                        df.write(" ".join(cmd) + "\n")
                    logger.info("Wrote ffmpeg debug file: %s", debug_file)
                except Exception:
                    logger.exception("Failed to write ffmpeg debug file")
        except Exception:
            logger.exception("Error while deciding to dump ffmpeg debug file")

        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"❌ FFmpeg merge_caption failed: {result.stderr}")
            raise RuntimeError("merge_caption ffmpeg failed")
        logger.info(f"✅ Caption merged successfully → {out_path}")

        # If there's an ASS subtitle alongside the workdir, burn it into the
        # output to provide per-word highlighting. Look for captions.ass in
        # the same directory as out_path.
        try:
            ass_candidate = Path(out_path).parent / "captions.ass"
            if ass_candidate.exists():
                burned = Path(out_path).with_name(Path(out_path).stem + "_subbed.mp4")
                # ffmpeg subtitles filter expects paths with colons/backslashes
                # escaped on Windows. Replace backslashes and colons appropriately.
                # Run ffmpeg with working dir set to the run folder and pass a
                # relative subtitle filename. This avoids issues where the
                # Windows drive letter (C:) is parsed as an option by the
                # subtitles/ass filter.
                rel_sub = ass_candidate.name

                # Try multiple subtitle filter variants to handle different ffmpeg builds
                attempts = [f"subtitles={rel_sub}", f"ass={rel_sub}"]
                for filt in attempts:
                    burn_cmd = [
                        "ffmpeg", "-y", "-i", str(out_path), "-vf",
                        filt, "-c:a", "copy", str(burned)
                    ]
                    logger.info("Running burn command: %s (cwd=%s)", " ".join(burn_cmd), str(ass_candidate.parent))
                    bres = subprocess.run(burn_cmd, check=False, capture_output=True, text=True, cwd=str(ass_candidate.parent))
                    logger.info("Attempt filter=%s exit=%s", filt, bres.returncode)
                    logger.info("Burn stdout: %s", bres.stdout)
                    logger.info("Burn stderr: %s", bres.stderr)
                    if bres.returncode == 0 and Path(burned).exists():
                        logger.info(f"✅ Burned ASS subtitles using {filt} → {burned}")
                        return str(burned)
                    else:
                        logger.warning("Attempt with filter %s failed (rc=%s).", filt, bres.returncode)
                        try:
                            log_file = ass_candidate.parent / "burn_subtitles.log"
                            with open(log_file, "a", encoding="utf-8") as lf:
                                lf.write(f"\n--- Attempt filter={filt} rc={bres.returncode} ---\n")
                                lf.write(bres.stderr or "(no stderr)")
                        except Exception:
                            logger.exception("Failed to write burn_subtitles.log")

        except Exception:
            logger.exception("Error while trying to burn ASS subtitles")

        return str(out_path)

    except Exception as e:
        logger.error(f"💥 merge_caption error: {e}")
        raise
