# Horror Story Video Automation

A Python and Remotion pipeline for producing narrated horror-story videos.
It selects a topic, generates a multipart script, prepares media and narration,
builds composition props, and can render and upload the resulting videos.

## Pipeline

1. `scripts/daily_topic_selector.py` selects a topic and consults topic history.
2. `scripts/script_gen.py` generates the story structure.
3. `scripts/props_builder.py`, `audio_gen.py` and `asset_fetcher.py` prepare audio,
   visuals and composition data.
4. `remotion-video/` renders the React-based video composition.
5. `scripts/uploader.py` handles configured YouTube publication.

## Prerequisites and setup

The workflows use Python 3.10, Node.js 20 and FFmpeg. Provider calls require
your own credentials and quota. Install dependencies from the repository root:

```sh
python -m venv .venv
```

Activate the virtual environment, then:

```sh
python -m pip install -r scripts/requirements.txt
cd remotion-video
npm install
npx remotion browser install
```

Return to the repository root and configure the providers used by your chosen
path. Environment-variable names and CI setup are documented in
`.github/workflows/daily_upload.yml` and `.github/workflows/upload.yml`.
Never commit real provider credentials or YouTube OAuth token files.

## Generate and inspect

```sh
python -m scripts.orchestrator --topic "An abandoned mountain lodge"
```

This can call external providers and generate assets. It does not request upload
unless the upload flag is supplied. Add `--render` to render a local video.
The separate `--upload` flag renders and publishes; use it only after reviewing
the generated media and intended destination channel.

To inspect the composition visually:

```sh
cd remotion-video
npm run dev
```

## Checks and current scope

```sh
cd remotion-video
npm run lint
npm run build
```

The `scratch/` scripts are provider experiments rather than a comprehensive
regression suite. Scheduled workflows may publish when enabled with working
credentials. Review scripts, narration, captions, media rights and platform
requirements before enabling scheduled publication. Workflow success is not
independent verification of content quality or delivery to an audience.

Built as an automation project by Sudip Parajuli / Techwired Solutions.
