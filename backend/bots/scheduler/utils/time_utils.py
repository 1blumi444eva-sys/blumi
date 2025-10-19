import random
from datetime import datetime, timedelta

BEST_TIMES = {
    "youtube": ["10:00", "13:00", "18:00"],
    "tiktok": ["09:00", "12:00", "20:00"],
    "instagram": ["11:00", "14:00", "19:00"],
    "facebook": ["08:00", "13:00", "17:00"]
}

async def get_next_post_times(config):
    freq = config["frequency_per_day"]
    if config["mode"] == "manual":
        return [datetime.strptime(t, "%H:%M").time() for t in config["custom_times"]]

    # Combine all best times across selected platforms
    all_times = []
    for p in config["platforms"]:
        all_times.extend(BEST_TIMES.get(p, []))

    # Pick random times weighted by frequency
    unique_times = random.sample(all_times, min(freq, len(all_times)))
    return [datetime.strptime(t, "%H:%M").time() for t in sorted(unique_times)]
