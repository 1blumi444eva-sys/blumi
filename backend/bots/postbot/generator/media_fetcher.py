import requests, os
import asyncio

async def fetch_media(topic: str):
    await asyncio.sleep(1)
    return [f"/content/fake_video_{hash(topic)}.mp4"]

PEXELS_API = os.getenv("PEXELS_API_KEY")

def fetch_video(topic, out_path):
    headers = {"Authorization": PEXELS_API}
    r = requests.get(f"https://api.pexels.com/videos/search?query={topic}&per_page=1", headers=headers)
    if r.ok and r.json().get("videos"):
        link = r.json()["videos"][0]["video_files"][0]["link"]
        data = requests.get(link)
        open(out_path, "wb").write(data.content)
        return out_path
    raise RuntimeError("No Pexels video found.")
