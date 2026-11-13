#!/usr/bin/python3
"""Check A5 travel time (Towcester -> Stony Stratford) via Google, record it in Redis,
and send an ntfy notification only when traffic gets genuinely bad.

Redis keys
  traffic_stats   stream  one entry per run: duration, baseline, delay, distance, day
  traffic_latest  hash    most recent reading, for Grafana stat panels
  traffic_alert   hash    alert state machine (level, pending, streak); expires at midnight
  traffic_alerts  stream  one entry per notification sent
"""
import logging
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import googlemaps
import redis
import requests

# --- Config ---
API_KEY = os.environ["API_KEY"]
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
NTFY_URL = os.environ.get("NTFY_URL", "https://ntfy.sh/towcestera5alerts")

# Delay (seconds over the free-flow time) that counts as bad traffic.
BAD_DELAY = int(os.environ.get("BAD_DELAY", "600"))
# Delay below which an alert is considered cleared. Gap between the two stops flapping.
CLEAR_DELAY = int(os.environ.get("CLEAR_DELAY", "300"))
# Route longer than this means Google has routed us off the A5 entirely.
DISTANCE_THRESHOLD = int(os.environ.get("DISTANCE_THRESHOLD", "9800"))
# Consecutive readings needed before a state change is believed.
CONFIRM_RUNS = int(os.environ.get("CONFIRM_RUNS", "2"))
# Send a "back to normal" message when an alert clears.
NOTIFY_CLEAR = os.environ.get("NOTIFY_CLEAR", "0") == "1"

ORIGIN = (52.122268, -0.973021)   # Towcester racecourse
DEST = (52.066852, -0.8714004)    # Stony Stratford

LEVEL_NORMAL, LEVEL_BAD, LEVEL_TERRIBLE = 0, 2, 3
LEVEL_NAMES = {LEVEL_NORMAL: "normal", LEVEL_BAD: "bad", LEVEL_TERRIBLE: "terrible"}

LONDON = ZoneInfo("Europe/London")

logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("traffic")


def midnight_tonight(now):
    return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def classify(delay, distance):
    """Map a reading to a level, or None when it sits in the hysteresis band."""
    if distance > DISTANCE_THRESHOLD:
        return LEVEL_TERRIBLE
    if delay >= BAD_DELAY:
        return LEVEL_BAD
    if delay < CLEAR_DELAY:
        return LEVEL_NORMAL
    return None


def notify(r, level, title, body, tags, traffic_text):
    log.info("notify: %s - %s", title, traffic_text)
    r.xadd("traffic_alerts", {"level": level, "title": title, "text": traffic_text})
    try:
        requests.post(NTFY_URL, data=body, headers={"Title": title, "Tags": tags}, timeout=10)
    except requests.RequestException as e:
        log.error("ntfy failed: %s", e)


def main():
    now = datetime.now(LONDON)
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    # --- Fetch ---
    gmaps = googlemaps.Client(key=API_KEY)
    result = gmaps.distance_matrix(ORIGIN, DEST, departure_time="now")
    element = result["rows"][0]["elements"][0]
    if result["status"] != "OK" or element["status"] != "OK":
        log.error("Google returned status %s / %s", result["status"], element["status"])
        sys.exit(1)

    duration = element["duration_in_traffic"]["value"]
    traffic_text = element["duration_in_traffic"]["text"]
    baseline = element["duration"]["value"]
    distance = element["distance"]["value"]
    delay = duration - baseline

    # --- Record ---
    reading = {"duration": duration, "baseline": baseline, "delay": delay,
               "distance": distance, "day": now.weekday()}
    r.xadd("traffic_stats", reading)

    # --- Alert state machine ---
    state = r.hgetall("traffic_alert")
    level = int(state.get("level", LEVEL_NORMAL))
    pending = int(state.get("pending", -1))
    streak = int(state.get("streak", 0))

    observed = classify(delay, distance)
    log.info("duration %ss (%s) baseline %ss delay %ss distance %sm | level=%s observed=%s pending=%s streak=%s",
             duration, traffic_text, baseline, delay, distance,
             LEVEL_NAMES[level], LEVEL_NAMES.get(observed, "hold"), LEVEL_NAMES.get(pending, "-"), streak)

    if observed is None:
        pass  # in the hysteresis band: keep any pending change alive but don't advance it
    elif observed == level:
        pending, streak = -1, 0
    else:
        if observed == pending:
            streak += 1
        else:
            pending, streak = observed, 1

        if streak >= CONFIRM_RUNS:
            previous, level = level, observed
            pending, streak = -1, 0
            if level == LEVEL_TERRIBLE:
                notify(r, level, "Traffic is terrible",
                       f"Heavy traffic means the A5 is no longer viable\nTravel time is currently: {traffic_text}",
                       "rotating_light,construction", traffic_text)
            elif level == LEVEL_BAD and previous < LEVEL_BAD:
                notify(r, level, "Traffic is bad",
                       f"Travel time is currently: {traffic_text}",
                       "rotating_light", traffic_text)
            elif level == LEVEL_NORMAL and NOTIFY_CLEAR:
                notify(r, level, "Traffic is back to normal",
                       f"Travel time is currently: {traffic_text}",
                       "white_check_mark", traffic_text)
            else:
                log.info("level %s -> %s (silent)", LEVEL_NAMES[previous], LEVEL_NAMES[level])

    pipe = r.pipeline()
    pipe.hset("traffic_alert", mapping={"level": level, "pending": pending, "streak": streak})
    pipe.expireat("traffic_alert", int(midnight_tonight(now).timestamp()))
    pipe.hset("traffic_latest", mapping={**reading, "text": traffic_text, "level": level,
                                         "updated": now.isoformat(timespec="seconds")})
    pipe.execute()


if __name__ == "__main__":
    main()
