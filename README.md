# Atmospheric horror automation

Three manually dispatched GitHub Actions workflows replace the two duplicate daily upload schedules:

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

## Social publishing

Generate and review `runs/current/post.jpg`, `caption.txt` and `post.json`. `text` creates a text card with an opening excerpt; the complete micro-story is in the caption. Facebook publishes that variant as native text. `photo` uses a darkened stock photo with title/opening text and a caption. Instagram always uses the JPEG plus caption, including the text-card variant. Captions over 2,200 characters or overflowing cards fail for revision.

For Facebook Login integration, configure a Page access token, Page ID, connected Instagram professional account ID and a supported Graph API version. Grant Page publishing permissions (`pages_manage_posts`, appropriate Page access/engagement permissions) and `instagram_basic` / `instagram_content_publish` for Instagram. App review/access requirements depend on which accounts you manage. Follow [Meta Page publishing](https://developers.facebook.com/docs/graph-api/reference/page/feed/) and [Instagram content publishing](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/content-publishing/).

Facebook photo uploads use the local file. Instagram fetches media from a public HTTPS URL: host the reviewed `post.jpg` yourself and set `INSTAGRAM_IMAGE_URL`. An authenticated Actions artifact URL or local file path will not work. Hosting is intentionally not provisioned by this repository.

```sh
python -m scripts.orchestrator --workflow social --post-file runs/current/post.json --upload --platforms facebook
# After hosting the reviewed image and setting INSTAGRAM_IMAGE_URL:
python -m scripts.orchestrator --workflow social --post-file runs/current/post.json --upload --platforms instagram
```

In GitHub Actions, first run the social workflow with `prepared_run_id` blank and download the `social-output` artifact for review. To publish that exact artifact, rerun with its generation run ID and the desired destinations. For Instagram, also supply the hosted image URL. Publication receipts are included in the resulting artifact. Use the latest receipt-bearing run ID for retries after partial success; rerunning the original generation artifact can create duplicate posts. Do not rerun an uncertain network failure until checking the platform.

Video workflows expose an explicit publish switch and private/unlisted/public visibility. They generate a new story on each run; reruns can create new uploads. No schedule is enabled. No external content is published simply by installing this code.

## Validation

```sh
python -m unittest discover -s tests -v
python -m compileall -q scripts
cd remotion-video
npm run lint
npm run build
```

Offline tests cover duration boundaries, part limits, stock fallback, card generation and publication preflight/receipts. Live provider generation and real uploads require your credentials and a manual end-to-end check.

## Existing GitHub secrets: META_USER_TOKEN and FACEBOOK_ID

The social workflow accepts these exact secret names. `FACEBOOK_ID` must be your
**Page ID**, not your personal Facebook user ID. At publication time the user
token is used to request a Page access token; neither token is printed or saved
in artifacts. The connected Instagram professional account ID is discovered
from the Page automatically. You can override it with `INSTAGRAM_ACCOUNT_ID`
as a secret or repository variable. An existing `META_ACCESS_TOKEN` Page token
still takes precedence, so remove a stale one before switching to a user token.

The user token needs `pages_show_list`, `pages_read_engagement`,
`pages_manage_posts` for Facebook posting and `instagram_basic`,
`instagram_content_publish` for Instagram. Request permissions through the same
Meta app used for the token. Keep `META_GRAPH_API_VERSION` as a repository
variable. Instagram additionally needs the exact reviewed JPEG hosted at the
public HTTPS image URL supplied to the workflow.

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
