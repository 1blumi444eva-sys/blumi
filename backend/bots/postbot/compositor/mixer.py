import subprocess

def mix_audio_video(video_path, audio_path, out_path):
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path, "-i", audio_path,
        "-c:v", "copy", "-c:a", "aac", "-shortest",
        out_path
    ]
    subprocess.run(cmd, check=True)
    return out_path
