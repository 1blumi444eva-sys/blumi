# BLUMI (v0 - Scaffold)
Production assistant to turn **outline → script → audio → (future) animation → clips → posting**.

This is a **modular scaffold** you can extend. Today it runs **end-to-end in dry‑run mode** (no external APIs).
It creates artifacts in `./artifacts/` and logs each step.

## Quickstart
```bash
# 1) Create & activate a venv (recommended)
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Install dependencies (only pillow is used in dry-run for images; others are optional)
pip install -r requirements.txt

# 3) Run the example pipeline
python -m blumi.pipeline --outline examples/outline_example.md --project my_first_project
```

Artifacts will appear under `./artifacts/my_first_project/`:
- `script.json` – parsed script
- `voices/` – placeholder "audio" files (text stubs for now)
- `storyboards/` – simple PNG cards per scene (for review)
- `episode_plan.json` – ordered plan the editor would follow
- `clips_plan.json` – suggested Shorts/Clips cut points
- `post_plan.json` – suggested titles/descriptions/tags for platforms

## Modules & Roadmap
- `modules/story.py` – outline → script generator (templates + constraints)
- `modules/tts.py` – script → voices (stub now; wire ElevenLabs/OpenAI TTS later)
- `modules/animation.py` – script+audio → scenes (stub; Blender/Daz pipeline later)
- `modules/editing.py` – scenes → episode (stub; MoviePy/FFmpeg later)
- `modules/clipping.py` – episode → vertical clips plan (ready)
- `modules/posting.py` – auto-posting plan (YouTube/TikTok APIs later)
- `modules/analytics.py` – pulls KPIs and suggests improvements (stub)
- `pipeline.py` – orchestrator CLI

## Configure
Edit `blumi/config.py` to set defaults (paths, seed, output sizes). Secrets for APIs will go in `.env` (not included).

## Notes
- This scaffold is **safe to run offline**.
- Replace stubs with real integrations progressively.
- Keep commits small: one module improvement at a time.
