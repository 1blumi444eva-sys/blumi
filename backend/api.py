# backend/api.py
# Try to import FastAPI and related classes; if unavailable (editor/CI), provide
# lightweight stubs so static analysis doesn't flag unresolved imports.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Provide lightweight type aliases so editors without FastAPI installed
    # don't flag unresolved imports; these aliases are only used by type checkers.
    from typing import Any as FastAPI, Any as BackgroundTasks, Any as HTTPException
    from typing import Any as CORSMiddleware
    from typing import Any as FileResponse, Any as JSONResponse

import importlib.util

# Prefer runtime import when available; use lightweight stubs otherwise.
if importlib.util.find_spec("fastapi") is not None:
    try:
        # Allow static analyzers to ignore missing fastapi in editor/CI while keeping a runtime import when available.
        from fastapi import FastAPI, BackgroundTasks, HTTPException  # type: ignore
    except Exception:
        # If a direct import somehow fails despite fastapi being discoverable,
        # provide minimal runtime-compatible fallbacks so editors/CI don't break.
        class FastAPI:
            def __init__(self, *args, **kwargs):
                pass
            def add_middleware(self, *a, **k):
                pass
            def get(self, *a, **k):
                def decorator(f):
                    return f
                return decorator
            def post(self, *a, **k):
                def decorator(f):
                    return f
                return decorator

        class BackgroundTasks:
            def __init__(self, *args, **kwargs):
                pass
            def add_task(self, *a, **k):
                pass

        class HTTPException(Exception):
            def __init__(self, status_code: int, detail: str | None = None):
                super().__init__(detail)
    try:
        from fastapi.middleware.cors import CORSMiddleware  # type: ignore
    except Exception:
        # Import starlette only if it's actually available at runtime; otherwise
        # provide a minimal fallback so editors/CI without starlette don't fail.
        if importlib.util.find_spec("starlette.middleware.cors") is not None:
            try:
                from starlette.middleware.cors import CORSMiddleware  # type: ignore
            except Exception:
                class CORSMiddleware:
                    pass
        else:
            class CORSMiddleware:
                pass
    from fastapi.responses import FileResponse, JSONResponse  # type: ignore
else:
    # Minimal runtime-safe stubs for environments without FastAPI installed.
    # These stubs allow the module to be opened in editors / linters without
    # failing import resolution; when FastAPI is installed, the real classes
    # above will be used instead.
    class FastAPI:
        def __init__(self, *args, **kwargs):
            pass
        def add_middleware(self, *a, **k):
            pass
        def get(self, *a, **k):
            def decorator(f):
                return f
            return decorator
        def post(self, *a, **k):
            def decorator(f):
                return f
            return decorator

    class BackgroundTasks:
        def __init__(self, *args, **kwargs):
            pass
        def add_task(self, *a, **k):
            pass

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str | None = None):
            super().__init__(detail)

    class CORSMiddleware:
        pass

    class FileResponse:
        def __init__(self, path, media_type=None, filename=None):
            self.path = path

    class JSONResponse(dict):
        def __new__(cls, content):
            return content
try:
    from pydantic import BaseModel  # type: ignore
except Exception:
    # Minimal BaseModel fallback so editors/CI without pydantic installed
    # can still open and run lightweight flows; mimics pydantic's dict() behavior.
    class BaseModel:
        def __init__(self, **data):
            for k, v in (data or {}).items():
                setattr(self, k, v)

        def dict(self):
            return dict(self.__dict__)

        def __iter__(self):
            # Allow dict(instance) to work by yielding (key, value) pairs
            return iter(self.__dict__.items())

        @classmethod
        def parse_obj(cls, obj):
            if isinstance(obj, cls):
                return obj
            if isinstance(obj, dict):
                return cls(**obj)
            # Fallback: try to build from attributes
            return cls(**getattr(obj, "__dict__", {}) or {})

from pathlib import Path
from datetime import datetime
import os, uuid, json, asyncio, shutil, threading
# Robustly import load_dotenv and uvicorn (editors/CI may not have these installed)
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    # No-op fallback so editors/CI without python-dotenv don't error
    def load_dotenv(*args, **kwargs):
        return False

try:
    import uvicorn  # type: ignore
except Exception:
    # Minimal stub so module can be imported in environments without uvicorn.
    class _UvicornStub:
        @staticmethod
        def run(*args, **kwargs):
            raise RuntimeError(
                "uvicorn is not installed. Install with 'pip install uvicorn' to run the server."
            )
    uvicorn = _UvicornStub()

load_dotenv()

# Module-level roots and job store so background tasks and helpers can access them
ROOT = Path.cwd() / "backend" / "bots" / "postbot"
CONTENT_ROOT = ROOT / "content"
HISTORY_ROOT = ROOT / "history"
POSTED_ROOT = ROOT / "posted"
JOBS: dict = {}

def create_app() -> FastAPI:
    app = FastAPI(title="Blumi API")

    # ✅ CORS: allow frontend to connect locally + in production
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://your-render-service.onrender.com",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # -------------------------------------------------
    # 🌱 Scheduler + Core Setup
    # -------------------------------------------------
    for d in (CONTENT_ROOT, HISTORY_ROOT, POSTED_ROOT):
        d.mkdir(parents=True, exist_ok=True)
    # -------------------------------------------------
    # Use the module-level ROOT/CONTENT_ROOT/HISTORY_ROOT/POSTED_ROOT
    # (already defined near module top). Ensure directories exist.
    for d in (CONTENT_ROOT, HISTORY_ROOT, POSTED_ROOT):
        d.mkdir(parents=True, exist_ok=True)

    # Scheduler is optional during lightweight local runs. Import it
    # lazily and continue if scheduler dependencies are missing (for
    # example when running on Python versions that some packages
    # don't support). If unavailable, we respond with an informative
    # message from the scheduler endpoints.
    try:
        from backend.bots.scheduler.scheduler_core import run_scheduler
        scheduler_available = True
    except Exception:
        run_scheduler = None
        scheduler_available = False
    scheduler_thread = None
    STATE_FILE = "backend/bots/scheduler/state.json"

    def read_state():
        if not os.path.exists(STATE_FILE):
            return {"active": False, "next_times": [], "last_post": None}
        with open(STATE_FILE, "r") as f:
            return json.load(f)

    def write_state(data):
        with open(STATE_FILE, "w") as f:
            json.dump(data, f, indent=4)

    # -------------------------------------------------
    # 🧠 Routes
    # -------------------------------------------------
    @app.get("/")
    async def root():
        return {"message": "Welcome to the Blumi API! 🚀"}

    @app.get("/status/test")
    async def status_test():
        return {"status": "ok", "message": "API is live and responsive."}

    @app.get("/scheduler/status")
    async def scheduler_status():
        return read_state()

    @app.post("/scheduler/start")
    async def start_scheduler(background_tasks: BackgroundTasks):
        global scheduler_thread
        if not scheduler_available:
            return {"status": "error", "message": "Scheduler unavailable (missing optional dependencies)."}
        config_path = "backend/bots/scheduler/config/schedule.json"
        if not os.path.exists(config_path):
            return {"status": "error", "message": "Schedule config not found."}

        with open(config_path, "r") as f:
            config = json.load(f)

        if scheduler_thread and scheduler_thread.is_alive():
            return {"status": "running", "message": "Scheduler already active."}

        def run_background():
            asyncio.run(run_scheduler(config))

        scheduler_thread = threading.Thread(target=run_background, daemon=True)
        scheduler_thread.start()

        state = read_state()
        state["active"] = True
        write_state(state)

        return {"status": "ok", "message": "Scheduler started successfully."}

    @app.post("/scheduler/stop")
    async def stop_scheduler():
        global scheduler_thread
        state = read_state()
        if scheduler_thread and scheduler_thread.is_alive():
            state["active"] = False
            write_state(state)
            scheduler_thread = None
    # -------------------------------------------------
    # 🎬 PostBot Core
    # -------------------------------------------------
    # 🎬 PostBot Core
    # -------------------------------------------------

    class RunPayload(BaseModel):
        topic: str
        style: str = "post"
        theme: str = "auto"
        font: str = "Arial"
        voice_id: str | None = None
        save_preview: bool = True
        # Structured caption settings passed from the frontend. Use a nested
        # Pydantic model for validation and conversion.
        class Caption(BaseModel):
            placement: str | None = "auto"
            hue: int | None = None
            font: str | None = None
            font_size: int | None = None

        caption: Caption | None = None

    @app.post("/run")
    async def run_postbot(payload: RunPayload, background: BackgroundTasks):
        job_id = uuid.uuid4().hex[:12]
        workdir = CONTENT_ROOT / job_id
        workdir.mkdir(parents=True, exist_ok=True)

        JOBS[job_id] = {
            "created_at": datetime.utcnow().isoformat(),
            "status": "queued",
            "progress": 0,
            "message": "Queued",
            "workdir": str(workdir),
            "final": None,
        }

        # Use BaseModel.dict() to convert nested models into plain dicts before
        # passing to the background job. This ensures downstream code expects
        # a plain dict for caption settings.
        try:
            pdata = payload.dict()
        except Exception:
            # Fallback for environments where BaseModel is a minimal stub
            pdata = dict(payload)

        background.add_task(_run_job_task, job_id, pdata)
        return {"job_id": job_id}

    @app.get("/voices")
    async def list_voices():
        """Return available ElevenLabs voices when ELEVEN_API_KEY is configured.

        The endpoint calls ElevenLabs API using the server-side API key loaded
        from the environment (`ELEVEN_API_KEY`). If the key is missing or the
        http client is not available, return an informative response with an
        empty list.
        """
        key = os.getenv("ELEVEN_API_KEY")
        if not key:
            return JSONResponse({"ok": False, "message": "ELEVEN_API_KEY not configured", "voices": []})

        # use a small server-side cache to avoid rate-limiting or high latency
        from backend.tools.voices_cache import get_cached_voices

        def fetch():
            import requests

            resp = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": key}, timeout=6)
            data = resp.json()
            voices_raw = data.get("voices") or data.get("data") or []
            voices = []
            for v in voices_raw:
                # normalize different shapes
                if isinstance(v, dict):
                    vid = v.get("voice_id") or v.get("id") or v.get("voice") or v.get("uuid")
                    name = v.get("name") or v.get("label") or str(vid)
                    if vid:
                        voices.append({"id": vid, "name": name})
            return voices

        try:
            voices = get_cached_voices(fetch, ttl=60)
            return JSONResponse({"ok": True, "voices": voices})
        except Exception as e:
            return JSONResponse({"ok": False, "message": str(e), "voices": []}, status_code=500)

    # --- Fonts endpoints ---
    # Provide a short curated list of common fonts and a full listing endpoint.
    SHORT_FONTS = ["Orbitron", "Montserrat", "Poppins", "Roboto", "Open Sans", "Lato", "Inter", "Oswald"]

    @app.get("/fonts")
    async def fonts_short():
        return JSONResponse({"ok": True, "fonts": SHORT_FONTS, "see_all": True})

    @app.get("/fonts/all")
    async def fonts_all():
        # Returns a longer list — static for now
        all_fonts = SHORT_FONTS + ["Merriweather", "Noto Sans", "Playfair Display", "Source Sans 3", "Raleway", "Ubuntu"]
        return JSONResponse({"ok": True, "fonts": all_fonts})

    class InstallPayload(BaseModel):
        name: str

    @app.post("/fonts/install")
    async def install_font_api(payload: InstallPayload):
        try:
            from backend.tools.font_installer import install_font
        except Exception as e:
            return JSONResponse({"ok": False, "message": f"font_installer missing: {e}"}, status_code=500)

        try:
            path = install_font(payload.name)
            return JSONResponse({"ok": True, "path": str(path)})
        except Exception as e:
            return JSONResponse({"ok": False, "message": str(e)}, status_code=500)

    @app.get("/status/{job_id}")
    async def get_status(job_id: str):
        job = JOBS.get(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        return JSONResponse(job)

    @app.get("/download/{job_id}")
    async def download_final(job_id: str):
        job = JOBS.get(job_id)
        if not job or job.get("status") != "done":
            raise HTTPException(404, "Final not available")

        posted = Path(job.get("final_copy", ""))
        if posted.exists():
            return FileResponse(posted, media_type="video/mp4", filename=posted.name)

        final = Path(job.get("final", ""))
        if final.exists():
            return FileResponse(final, media_type="video/mp4", filename=final.name)

        raise HTTPException(404, "File missing")

    @app.post("/upload_tiktok")
    async def upload_tiktok(payload: dict):
        """
        Simulated TikTok upload endpoint. Expects JSON: { job_id: str, video_url: str }
        If credentials are configured, this could be replaced with a real TikTok SDK call.
        For now we log the attempt to POSTED_ROOT/uploads.log and return a simulated response.
        """
        job_id = payload.get("job_id")
        video_url = payload.get("video_url")
        log_entry = {
            "time": datetime.utcnow().isoformat(),
            "job_id": job_id,
            "video_url": video_url,
            "status": "simulated",
            "message": "Logged upload attempt (no credentials)"
        }
        try:
            POSTED_ROOT.mkdir(parents=True, exist_ok=True)
            log_file = POSTED_ROOT / "uploads.log"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
            return JSONResponse({"ok": True, "message": "Simulated upload logged", "entry": log_entry})
        except Exception as e:
            return JSONResponse({"ok": False, "message": str(e)}, status_code=500)

    return app

async def _run_job_task(job_id: str, payload: dict):
    JOBS[job_id]["status"] = "running"
    JOBS[job_id]["message"] = "Starting run"

    try:
        # Try the two likely locations for make_video. Capture
        # detailed errors so the job status shows the underlying
        # import failure (helps debugging missing deps/runtime
        # issues during import-time).
        make_video = None
        import_errs = []
        try:
            # Try importing the common location first. Use importlib to avoid
            # static analyzers reporting missing imports for optional modules.
            import importlib

            try:
                mod = importlib.import_module("backend.main")
                make_video = getattr(mod, "make_video", None)
            except Exception as e1:
                import_errs.append(f"backend.main import error: {e1}")

            if make_video is None:
                try:
                    mod2 = importlib.import_module("backend.bots.postbot.main")
                    make_video = getattr(mod2, "make_video", None)
                except Exception as e2:
                    import_errs.append(f"backend.bots.postbot.main import error: {e2}")
        except Exception:
            # Fall through and let the later check raise an informative ImportError
            pass
        # If make_video isn't present in locals OR resolved to None, raise ImportError.
        # Previous logic used `and` which allowed calling a None make_video when the
        # symbol existed but was None. Use `or` so we fail fast and provide import errors.
        if ('make_video' not in locals()) or (make_video is None):
            raise ImportError("; ".join(import_errs) or "Could not import make_video")
        workdir = Path(JOBS[job_id]["workdir"])
        JOBS[job_id]["message"] = "Generating narration & fetching media"

        final_path = await make_video(
            payload["topic"],
            payload["style"],
            payload["theme"],
            run_root=workdir,
            voice_id=payload.get("voice_id"),
            caption_settings=payload.get("caption"),
        )

        JOBS[job_id].update(
            {"status": "done", "progress": 100, "final": str(final_path)}
        )

        if payload.get("save_preview", True):
            dst = POSTED_ROOT / f"{job_id}.mp4"
            shutil.copyfile(final_path, dst)
            JOBS[job_id]["final_copy"] = str(dst)

    except Exception as e:
        # Capture full traceback so API clients and tests can see the
        # underlying error location (helps debug missing imports/name errors).
        import traceback
        tb = traceback.format_exc()
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["message"] = tb


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.api:create_app", host="0.0.0.0", port=port, reload=True, factory=True)
