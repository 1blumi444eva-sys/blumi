# backend/bots/scheduler/scheduler_core.py
import asyncio
import json
import os
from datetime import datetime
from backend.bots.scheduler.utils.time_utils import get_next_post_times
from backend.bots.scheduler.utils.post_utils import get_next_video, mark_posted
from backend.bots.scheduler.platforms import youtube_api, instagram_api, facebook_api
# TikTok temporarily disabled for demo (import error fix)
tiktok_api = None


STATE_FILE = "backend/bots/scheduler/state.json"

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def load_state():
    if not os.path.exists(STATE_FILE):
        save_state({"active": False, "next_times": [], "last_post": None})
    with open(STATE_FILE, "r") as f:
        return json.load(f)

async def run_scheduler(config):
    print("🌀 Scheduler loop started.")
    state = load_state()
    state["active"] = True
    post_times = await get_next_post_times(config)
    state["next_times"] = [pt.strftime("%H:%M") for pt in post_times]
    save_state(state)

    while state["active"]:
        now = datetime.now().strftime("%H:%M")
        for pt in post_times:
            if now == pt.strftime("%H:%M"):
                print(f"🕐 Time to post! ({pt})")
                await run_post_cycle(config)
                state["last_post"] = datetime.now().isoformat()
                save_state(state)
        await asyncio.sleep(60)
        state = load_state()  # reload in case stopped externally

    print("🛑 Scheduler stopped.")
