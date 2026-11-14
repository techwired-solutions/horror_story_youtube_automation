# Atmospheric horror automation

Three GitHub Actions workflows replace the two duplicate daily upload schedules. Social posting is automatic; video workflows retain their manual controls:

| Workflow | Output | Length / format |
| --- | --- | --- |
| Long-form horror video | YouTube landscape video | 8â€“20 minutes; optional 5-minute starter episode |
| Horror Shorts | YouTube portrait video | One complete story, or two narrative parts; each at most 180 seconds |
| Facebook and Instagram horror posts | Caption plus JPEG card or stock photo card | Facebook text-only or photo + text; Instagram image + caption |

## Editorial direction

One low, unhurried, intimate narrator; subtle dialogue changes; emotional vulnerability and slow psychological dread. Natural sentences, deliberate silence before revelations and occasional recurring phrases. No shouted delivery, forced subscribe beats, flashing transitions, bouncing word captions or jump-scare stingers. Scenery holds for about 18 seconds or longer with gentle zooms. Ambient audio stays low and loops beneath narration; source video audio is muted.

Scripts are original fiction unless you explicitly supply reviewed source notes and a source URL. Source-based stories are labeled dramatizations and paranormal claims remain unverified. The pipeline does not scrape or copy Reddit stories, or independently fact-check source notes. Review factual claims and rights before publishing.

## Setup

Python 3.11+, Node 22 and FFmpeg/ffprobe are required. From the repository root:

```sh
python -m venv .venv
# Activate .venv for your shell, then:
pip install -r scripts/requirements.txt
cd remotion-video
npm install
npx remotion browser install
cd ..
```

Copy `.env.example` to `.env` locally, or configure GitHub secrets and repository variables as indicated there. Provider availability, API quotas and narration services are separate from stock-media costs. At least one stock provider key and one script-provider key are needed for generated videos. Hume is tried first, Kokoro second, Edge TTS last; voice quality and timing differ by provider. Long scripts can exceed a provider's request limits: failures stop production rather than publish missing narration. The legacy Gemini SDK remains in use and should be migrated separately before it becomes unavailable.

## Local production

Run from the repository root. Generation prepares assets and JSON; `--render` renders; `--upload` also renders and uploads. Uploads default to private. These examples do not publish:

```sh
python -m scripts.orchestrator --workflow long --minutes 10 --topic "The room above the night shift" --render
python -m scripts.orchestrator --workflow short --topic "Someone answers the baby monitor" --render
python -m scripts.orchestrator --workflow social --variant text --topic "The last bus home"
python -m scripts.orchestrator --workflow social --variant photo --topic "The empty forest station"
```

Use distinct `--output-dir runs/episode-name` folders for separate episodes. The public Remotion media directory is shared: do not run video jobs concurrently in one checkout. Output includes story JSON, per-part props, rendered MP4s, stock credit sidecars, and publication receipts where applicable. Review/edit `story.json`, then reuse it with `--script-file runs/episode-name/story.json`. Do not reuse a publication receipt for a different story. Receipts skip known successful uploads, but a network failure after a platform accepted a write can still require manual reconciliation; they are not a platform-wide exactly-once guarantee.

For a sourced story:

```sh
python -m scripts.orchestrator --workflow long --minutes 8 --source-file work/source-notes.txt --source-url https://example.org/original-account --topic "The lighthouse keeper"
```

Supply those source arguments again when rendering an edited source-based script. Without source notes, the output is explicitly labeled fiction. Estimated Shorts length is checked before synthesis; actual audio plus the one-second tail is checked before rendering. If a part is too long, edit the script or split at a natural turning point and retry. Long-form audio must fall within 20% of the requested target and never exceed 20 minutes. The system fails rather than accelerate or truncate a story. Inspect narration and caption timing; provider timestamps or estimates can be imperfect.

## Free media and audio

Pexels then Pixabay supply stock videos and photos. Video searches fall back to photos. Missing visuals fail clearly; there is no paid or AI-image fallback. Credits include creator, source page and license URL, and video descriptions include visual credits. Stock is illustrative, not evidence that a story happened. Respect recognizable-person, trademark and other restrictions of each asset; free stock does not grant every possible use. Freesound searches are restricted to CC0; absent audio credentials produce silence. Review downloaded sound beds for unwanted transients before publishing.

Provider references: [Pexels API](https://www.pexels.com/api/documentation/), [Pexels license](https://www.pexels.com/license/), [Pixabay API](https://pixabay.com/api/docs/), [Pixabay license](https://pixabay.com/service/license-summary/), [YouTube three-minute Shorts](https://support.google.com/youtube/answer/15424877).

## Automatic Facebook and Instagram publishing

The social workflow runs every day at **20:02 Asia/Kathmandu (14:17 UTC)**.
GitHub may delay scheduled jobs. Optional manual runs have no input fields and
use the same daily state. A completed date is skipped, so clicking Run workflow
again does not intentionally create another pair of posts.

Each run creates an original fictional micro-story, automatically searches
Pexels and Pixabay for a photo, builds a dark 1080 x 1350 JPEG with a restrained
opening excerpt, and puts the full story in the caption. If stock is unavailable,
it uses a generated text card. Facebook alternates native text-only posts and
photo-with-text posts on successive dates. Instagram always gets the JPEG plus
caption; Instagram has no native text-only feed post.

There is no prepared-run ID, image URL, platform selection, topic field, manual
approval step or separate image-hosting account. The default destinations are
both Facebook and Instagram. Existing `META_USER_TOKEN` and `FACEBOOK_ID` secrets
are supported. `FACEBOOK_ID` is the Page ID. A Page token is obtained from the
user token and the linked Instagram Business/Creator account is discovered
automatically. A supplied `META_ACCESS_TOKEN` Page token takes precedence.

The same Meta app/token needs `pages_show_list`, `pages_read_engagement`,
`pages_manage_posts`, `instagram_basic` and `instagram_content_publish`, plus the
appropriate Page access. Connect your Instagram professional account to that
Page. App review/access requirements depend on which accounts you manage.
`INSTAGRAM_ACCOUNT_ID` is an optional secret/variable override.
`META_GRAPH_API_VERSION` is optional and defaults to supported version `v24.0`.

At least one script-provider key (`GEMINI_API_KEY` or `NVIDIA_NIM_API_KEY`) is
required. For stock imagery add `PEXELS_API_KEY` and/or `PIXABAY_API_KEY`. These
are free stock APIs with quotas; script services have their own quotas/pricing.
No paid image generation is used and arbitrary Google Images results are not
used because search results alone do not establish reuse rights.

### Automatic image hosting and retries

The workflow's built-in `GITHUB_TOKEN` writes only generated JPEGs, story/post
JSON and publication receipts to a separate `automation/social-media` branch.
The repository must be public. Instagram fetches the exact JPEG from an
immutable public GitHub raw URL, which the job verifies before publishing.
No additional hosting secret, Pages configuration, or manual upload is needed.
The social workflow needs Actions `contents: write`; organization/repository
policy must allow this. Credentials are never included in media or receipts.
Generated stories, images and post IDs on that branch are publicly visible.

Daily state lives under `social/YYYY-MM-DD/`, using the Kathmandu date. Reruns
reuse the saved story, image and successful publication receipts. Each confirmed
Facebook post and Instagram container/publication ID is persisted immediately.
An interrupted job can resume the pending destination without intentionally
republishing the successful one. Network failures after a platform accepts a
request but before its response is saved remain ambiguous: check the platform
before retrying such a failure. An expired Instagram container requires manual
reconciliation rather than blindly creating another post.

For manual local generation without publication, the original CLI remains:

```sh
python -m scripts.orchestrator --workflow social --variant photo --topic "The empty station"
```

The low-level manual publisher accepts a saved post and a hosted image URL;
the scheduled workflow handles both automatically. No local desktop process is
needed for daily social publishing. Long-form and Shorts workflows are unchanged.

## Validation

```sh
python -m unittest discover -s tests -v
python -m compileall -q scripts
cd remotion-video
npm run lint
npm run build
```

Offline tests cover duration boundaries, part limits, stock fallback, card generation and publication preflight/receipts. Live provider generation and real uploads require your credentials and a manual end-to-end check.

### Renew YouTube authorization

An expired access token refreshes automatically if its refresh token remains
valid. A revoked or expired refresh token requires interactive sign-in on your
computer. With the Google desktop OAuth client JSON saved locally as
`client_secret.json`, activate the environment and run:

```sh
python -m scripts.uploader
```

This authenticates only; it does not upload a video. If a refresh fails, it opens
the consent flow again locally. On Windows, copy the resulting credential into
the clipboard without printing it in terminal output:

```powershell
Set-Clipboard ([Convert]::ToBase64String([IO.File]::ReadAllBytes((Resolve-Path token.pickle))))
```

Replace the GitHub secret `YOUTUBE_TOKEN_PICKLE_BASE64` with the clipboard value.
Also keep `YOUTUBE_CLIENT_SECRET` set to the complete matching client JSON.
Never put these credentials in chat or commit them. Google external OAuth apps
in Testing normally issue refresh tokens that expire after seven days for
YouTube scopes; use the appropriate production OAuth configuration for durable
automation, completing any Google verification requirements that apply.
