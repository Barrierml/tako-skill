---
name: tako-skill
description: Use Tako for billed web search with sources, image generation/editing with one or multiple references, Grok video generation (text-to-video and image-to-video), and System One Choice/Score/Noul decisions. Use when the user wants these tasks through Tako; not for ordinary chat or speech.
---

# Tako Skill

Use one Tako user Key for search, images, video and structured decisions. Preserve the user's chosen model and task. Calls may consume account or subscription quota.

## Setup

The user configures `TAKO_API_KEY` with the complete console value, preserving its prefix. If missing, ask for it to be configured locally; never ask them to paste it into a public conversation. Do not print or commit credentials.

- Default root: `https://tako.shiroha.tech`; override with `TAKO_BASE_URL`.
- API auth: `Authorization: Bearer $TAKO_API_KEY`.
- `/v1` and `/api/v1` are compatible prefixes for the endpoints below. Native Gemini uses `/v1beta`.
- Helpers require Bash, Python 3 and curl. Resolve script paths relative to this skill's directory, not the user's project directory.
- Human installation and first-use instructions: [getting started](docs/getting-started.md).

## Choose the workflow

Read the relevant reference before constructing the request; load other references only when the task needs them.

| Task | Read | Helper / API |
| --- | --- | --- |
| Check token or billing usage | [usage](references/usage.md) | `scripts/tako-usage.sh`; read-only `GET /v1/usage/token/` or billing endpoints |
| Search and cite sources | [search](references/search.md) | `scripts/tako-search.sh`; `POST /v1/search` |
| Generate an image | [images](references/images.md) | `scripts/tako-image.sh generate`; `POST /v1/images/generations` |
| Edit one reference image | [images](references/images.md) | `scripts/tako-image.sh edit`; `POST /v1/images/edits` or native Gemini |
| Edit or combine multiple references | [multi-reference recipe](references/images.md#直接调用多张参考图) | Direct JSON `images[].image_url`; the helper takes one image |
| Generate a video (text-to-video or image-to-video) | [video](references/video.md) | `scripts/tako-video.sh generate`; `POST /v1/videos/generations` then poll `GET /v1/videos/{id}` |
| Classify, route, score or judge urgency | [System One](references/systemone.md) | `scripts/tako-systemone.sh` for one Noul; direct `POST /v1/systemone` for other question types |

Use a chat model for prose, code and conversation. Do not substitute chat-completions for search or System One. `jev-latest` is a decision model, not a chat model; `/v1/models` discovery is not guaranteed to list it. The public pricing catalog includes `jev-latest` as of 2026-10-04.

## Images: defaults and input boundaries

- Default `gpt-image-2`, one output. `wan2.7-image` and `wan2.7-image-pro` are also available when the user's group exposes the Alibaba image channel; preserve an explicit model choice and do not silently switch models.
- Helper routes GPT to multipart editing, Grok to JSON/base64, Gemini to native `generateContent` with `inlineData`. Read the guide for direct API formats.
- Gemini compatibility JSON/multipart edits were fixed in `tako-20261004-1212` and return `data[].b64_json`; the reference-loss/wrong-shape defect belongs to the older `tako-20261002-1433` build.
- Two references were jointly used by `gpt-image-2`, `gemini-3.1-flash-image`, and `grok-imagine-image-quality`. Grok's current upstream limits edit sources to three. GPT/Gemini maxima and other models' multi-image behavior were not verified.
- The helper and Playground accept one reference. Never silently discard additional user images or pass extra filenames in the helper's prompt position; use the direct multi-reference recipe.
- Adapt the [actual image examples](references/images.md#看效果三个生图例子与一次改图) to the task. For edits, preserve explicitly requested invariants and compare the result with the inputs.

Minimal helper invocation from the skill directory:

```bash
./scripts/tako-image.sh generate "a coral ceramic mug, warm product photography" \
  --out response.json --save-image output/mug.png
```

## Video: defaults and input boundaries

- Default `grok-imagine-video-1.5`, `480p`, 5 seconds — it produces better visual quality and motion coherence, accepts text-to-video and image-to-video (reference image optional for both models), and is the only model that supports `1080p`. `grok-imagine-video` remains an optional lighter alternative, limited to `480p`/`720p`. Duration is an integer 1–15 seconds.
- Video tasks are asynchronous: `generate` submits, polls until `SUCCESS`/`done`, then downloads the MP4 from `/v1/videos/{id}/content`. A finished MP4 is the only finished artifact — a 200 or a `SUCCESS` status alone is not a delivered video.
- The submitted response is saved with `--out` before polling, so a timed-out or failed poll can be resumed with `scripts/tako-video.sh status <task_id>` instead of paying for a new submission.

```bash
./scripts/tako-video.sh generate "a coral ceramic mug slowly rotating, product shot" \
  --duration 5 --resolution 480p --out task.json --save-video output/mug.mp4
```

## Deliver and recover

- Search: cite `results[].url` when present. An empty results array can accompany a valid `answer`; do not invent citations.
- Images: preserve a successful response with `--out`, save/decode actual bytes, report the emitted path and inspect the image. A 200 or base64 string alone is not a finished image artifact. Saving follows actual PNG/JPEG/WebP extension and refuses overwrites.
- System One: use `model=jev-latest` by default and read `answers`; a returned versioned model id is valid. Keep question types and criteria in the reference's schema.
- Usage: when the user asks about remaining quota, run the read-only usage helper before a paid operation. Distinguish current-token quota from account billing windows; never add the two values together.
- HTTP failures: inspect status and response. Search/System One curl helpers can exit zero on HTTP errors; process status alone is insufficient. `401/403` suggests Key/access, billing errors suggest account/subscription quota, `422` suggests malformed questions.
- Paid image calls: no automatic retries. On timeout, rate limits or saving failures, inspect usage and any saved response before deciding whether to repeat the request. Reuse a successful response to recover an image instead of regenerating.
- Video: same no-retry rule, and per-second billing makes blind resubmission costlier. On poll timeout or failure, reuse the saved task JSON with `status`/`--task-json`; only resubmit after confirming the task cannot be recovered.
- Send the Tako Key only to the configured API root, never to image or video CDNs. Do not follow API redirects that could forward credentials.

## Unsupported or unverified workflows

Do not use this skill for speech, image task polling, async/batch image APIs or `/v1/images/variations`. Do not assume masks, transparency, exact multi-reference preservation or every size/quality combination works across models.

Image behavior above was verified on 2026-10-04. Grok video generation was added to the API on 2026-11-16. Search and System One references describe the existing contract and earlier checks; they were not re-tested in that image verification. Troubleshooting: [common questions](docs/troubleshooting.md).
