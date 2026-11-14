"""Shared editorial rules and duration validation, independent of providers."""
import math

STYLE = """Use one consistent late-night narrator: low, unhurried, controlled,
slightly dry and intimate. Subtly color dialogue; never shout, use cartoon voices,
or theatrical accents. Build a relatable protagonist, emotional vulnerability,
psychological traps and anticipation. Favor concrete details over gore. Repeat a
short mysterious phrase sparingly and deliberately. Pause BEFORE a reveal by
ending the preceding beat with 1.2-2 seconds of silence. Use calm, unease, dread,
whisper, reveal or ending delivery. No forced subscribe beats or loud stingers.
Visuals: dark fog, monochrome, slow zooms, long holds; no chaotic cuts.
Always label invented events as fiction. For supplied factual source material,
distinguish documented facts from allegations, folklore and dramatization. Never
invent citations, quotations or claims that an imagined event really happened.
Use original wording; do not copy Reddit or other copyrighted stories."""


def validate_story(story, mode, minutes=10):
    if not isinstance(story, dict) or not isinstance(story.get("title"), str) or not story["title"].strip():
        raise ValueError("Story needs a nonempty title")
    parts = story.get("parts", [])
    if not isinstance(parts, list) or not 1 <= len(parts) <= (2 if mode == "short" else 1):
        raise ValueError("Shorts allow one or two parts; other formats require one")
    for number, part in enumerate(parts, 1):
        part["part_number"] = number
        beats = part.get("beats", [])
        if not beats:
            raise ValueError("Every part needs narration beats")
        estimate = 0
        for beat in beats:
            if not isinstance(beat.get("text"), str) or not beat["text"].strip():
                raise ValueError("Empty narration beat")
            pause = float(beat.get("pause_after", 0.6))
            if not math.isfinite(pause) or not 0 <= pause <= 3:
                raise ValueError("Invalid pause")
            beat.update(voice="male", animation_type="zoom", pause_after=pause)
            if beat.get("delivery") not in {"calm", "unease", "dread", "whisper", "reveal", "ending"}:
                beat["delivery"] = "dread"
            beat["duration_estimate"] = len(beat["text"].split()) / 1.9 + pause
            estimate += beat["duration_estimate"]
        if mode == "short" and estimate > 175:
            raise ValueError("Short part exceeds the safe narration estimate; rewrite before synthesis")
    return story


def check_render_duration(seconds, mode, minutes=10):
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("Invalid narration duration")
    # Includes the one-second video tail.
    if mode == "short" and seconds + 1 > 180:
        raise ValueError("Narration exceeds Shorts limit; rewrite/split at a story beat, never speed up or truncate")
    if mode == "long" and not (minutes * 60 * 0.8 <= seconds <= min(1200, minutes * 60 * 1.2)):
        raise ValueError("Long-form narration missed the requested duration; rewrite before rendering")
