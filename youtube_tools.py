# youtube_tools.py
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# YouTube API requires this scope
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_youtube_service():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(
            "client_secret.json", SCOPES
        )
        creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)

def upload_video(file_path, title, description, tags=None, privacy="public"):
    youtube = get_youtube_service()

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags or ["blumi", "motivation"],
                "categoryId": "22"  # People & Blogs
            },
            "status": {"privacyStatus": privacy},
        },
        media_body=file_path
    )
    response = request.execute()
    print(f"✅ Uploaded video: {response['id']}")
