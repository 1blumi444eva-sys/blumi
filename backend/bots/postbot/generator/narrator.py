# bots/postbot/generator/narrator.py
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_narration(topic: str, theme: str, style: str, target_seconds: int = 30):
    """
    Request a narration that fits target_seconds (±1s). We estimate words/sec ≈ 3.8,
    so target words = target_seconds * 3.8 (adjustable).
    """
    words_per_second = 3.8
    target_words = max(6, int(round(target_seconds * words_per_second)))

    prompt = (
        f"Write a short narration about '{topic}', tone: {theme}, style: {style}. "
        f"Produce approximately {target_words} words (aim for audio ~{target_seconds} seconds). "
        "Keep it punchy, natural, and ready-to-read for TTS. Return only the narration text."
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are a concise advertising copywriter."},
                  {"role": "user", "content": prompt}],
        max_tokens=target_words * 2,
        temperature=0.8,
    )
    narration = resp.choices[0].message["content"].strip()
    return narration
