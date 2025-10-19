from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path
import os, uuid, json, asyncio, shutil, threading
from datetime import datetime
from fastapi import BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # Default to 8000 locally
    uvicorn.run("backend.api:create_app", host="0.0.0.0", port=port, reload=True, factory=True)

def create_app():
    app = FastAPI(title="PostBot API")
    ...
    return app


# Initialize single FastAPI app
load_dotenv()
app = FastAPI(title="PostBot API (Blumi)")

# Allow React/Streamlit frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/status/test")
async def status_test():
    return {"status": "ok", "message": "API is live and responsive."}


# -------------------------------------------------
# 🌱 Environment Setup
# -------------------------------------------------
load_dotenv()
app = FastAPI(title="PostBot API (Blumi)")

ROOT = Path.cwd() / "backend" / "bots" / "postbot"
CONTENT_ROOT = ROOT / "content"
HISTORY_ROOT = ROOT / "history"
POSTED_ROOT = ROOT / "posted"
for d in (CONTENT_ROOT, HISTORY_ROOT, POSTED_ROOT):
    d.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------
# 🕒 Scheduler System
# -------------------------------------------------
from backend.bots.scheduler.scheduler_core import run_scheduler

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


@app.post("/scheduler/start")
async def start_scheduler(background_tasks: BackgroundTasks):
    """
    Starts the async scheduler loop that auto-posts content.
    Runs in a background thread so FastAPI stays responsive.
    """
    global scheduler_thread

    config_path = "backend/bots/scheduler/config/schedule.json"
    if not os.path.exists(config_path):
        return {"status": "error", "message": "Schedule config not found."}

    with open(config_path, "r") as f:
        config = json.load(f)

    # Prevent multiple schedulers
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
        return {"status": "stopped"}
    else:
        return {"status": "idle", "message": "Scheduler is not running."}


@app.get("/scheduler/status")
async def scheduler_status():
    return read_state()

@app.get("/status/test")
async def status_test():
    """
    Simple health check route.
    """
    return {"status": "ok", "message": "API running smoothly"}


# -------------------------------------------------
# ⚙️ Core PostBot Job Engine
# -------------------------------------------------
JOBS = {}


class RunPayload(BaseModel):
    topic: str
    style: str = "post"
    theme: str = "auto"
    font: str = "Arial"
    voice_id: str | None = None
    save_preview: bool = True


@app.post("/run")
async def run_postbot(payload: RunPayload, background: BackgroundTasks):
    """
    Accepts a topic + style and starts an async video generation task.
    """
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

    background.add_task(_run_job_task, job_id, dict(payload))
    return {"job_id": job_id}


async def _run_job_task(job_id: str, payload: dict):
    JOBS[job_id]["status"] = "running"
    JOBS[job_id]["progress"] = 2
    JOBS[job_id]["message"] = "Starting run"

    try:
        from backend.bots.postbot.main import make_video

        workdir = Path(JOBS[job_id]["workdir"])
        JOBS[job_id]["message"] = "Generating narration & fetching media"
        JOBS[job_id]["progress"] = 10

        final_path = await make_video(
            payload["topic"],
            payload["style"],
            payload["theme"],
            run_root=workdir,
        )

        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["progress"] = 100
        JOBS[job_id]["message"] = "Completed"
        JOBS[job_id]["final"] = str(final_path)

        if payload.get("save_preview", True):
            dst = POSTED_ROOT / f"{job_id}.mp4"
            shutil.copyfile(final_path, dst)
            JOBS[job_id]["final_copy"] = str(dst)

    except Exception as e:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["message"] = str(e)


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

# -------------------------------------------------
# 🧩 Demo Endpoints (for TikTok Video)
# -------------------------------------------------
@app.get("/status/test")
async def status_test():
    return {"status": "ok", "message": "API is live and responsive."}


@app.post("/tiktok/upload")
async def tiktok_upload():
    """
    Mock TikTok upload endpoint for demo video.
    Simulates uploading a video to TikTok's API.
    """
    await asyncio.sleep(1)  # Simulate network delay
    return {"status": "ok", "message": "video uploaded successfully"}


@app.post("/tiktok/publish")
async def tiktok_publish():
    """
    Mock publish step for TikTok Content Posting API.
    """
    await asyncio.sleep(1)
    return {"status": "ok", "message": "video published to TikTok"}
