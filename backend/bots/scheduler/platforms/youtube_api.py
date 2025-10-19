# bots/scheduler/platforms/youtube_api.py
import os
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

TOKEN_PATH = "bots/scheduler/platforms/token.pickle"
CLIENT_SECRET = "bots/scheduler/platforms/client_secret.json"

def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)


async def post(video):
    """
    Uploads a video file to the authenticated YouTube channel.
    video = { "path": "path/to/video.mp4", "title": "My Title", "description": "Desc", "tags": [...] }
    """
    youtube = get_authenticated_service()
    body = {
        "snippet": {
            "title": video.get("title", "Blumi AutoPost"),
            "description": video.get("description", "Uploaded via Blumi PostBot"),
            "tags": video.get("tags", ["Blumi", "AI", "Shorts"]),
            "categoryId": "22"  # People & Blogs
        },
        "status": {"privacyStatus": "public"}
    }

    media = MediaFileUpload(video["path"], chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()

    video_id = response.get("id")
    video_url = f"https://youtu.be/{video_id}"
    print(f"✅ Uploaded to YouTube: {video_url}")
    return video_url
