# backends/bots/scheduler/utils/post_utils.py
def get_next_video():
    return {"path": "sample.mp4", "title": "Test Video", "description": "Placeholder"}

def mark_posted(video):
    print(f"✅ Marked as posted: {video['path']}")
