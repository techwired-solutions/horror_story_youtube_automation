"""Prepare all narration before rendering; repair measured Shorts overruns."""
import json
from pathlib import Path
from loguru import logger
from scripts.story_policy import NarrationDurationError


def prepare_video_parts(story, builder, directory, mode, minutes, rewrite=None):
    directory = Path(directory)
    for attempt in range(3):
        prepared = []
        try:
            for part in story["parts"]:
                number = part["part_number"]
                title = story["title"] + (f" - Part {number}" if len(story["parts"]) > 1 else "")
                props_path = directory / f"props-{number}.json"
                props = builder.build_props(part, title, number, str(props_path), mode, minutes)
                if not props:
                    raise RuntimeError("Media preparation failed")
                video = (directory / f"part-{number}.mp4").resolve()
                prepared.append((title, props, video, props_path))
            return story, prepared
        except NarrationDurationError as error:
            if mode != "short" or rewrite is None or attempt == 2:
                raise
            logger.warning(f"Audio timing attempt {attempt + 1}/3 needs revision: {error}")
            revised = rewrite(story, str(error))
            if not revised:
                raise RuntimeError("Could not rewrite the story to fit measured narration duration") from error
            for key in ("story_kind", "disclosure"):
                if key in story:
                    revised[key] = story[key]
            story = revised
            (directory / "story.json").write_text(json.dumps(story, indent=2), encoding="utf-8")
    raise RuntimeError("Narration duration repair exhausted")
