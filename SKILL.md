---
name: tako-skill
description: Use Tako for billed web search with sources, image generation/editing with one or multiple references, Grok video generation (text-to-video, image-to-video, first/last-frame interpolation, multi-reference consistency, video editing and seamless extension), Bingtang TTS / emotion-instructed speech / zero-shot voice cloning / ASR transcription, cross-model architecture/code consultation, and System One Choice/Score/Noul decisions. Use when the user wants these tasks through Tako; not for ordinary chat.
---

# Tako Skill

Use one Tako user Key for search, images, video, speech (TTS, voice clone, ASR), cross-model consultation and structured decisions. Preserve the user's chosen model and task. Calls may consume account or subscription quota.

Desktop clients (Claude Desktop, Codex Desktop, Google Antigravity) can also mount Tako's built-in 6-in-1 Super MCP directly via [Tako Switch](https://tako.shiroha.tech/tako-switch).

## Setup

The user configures `TAKO_API_KEY` with the complete console value, preserving its prefix. If missing, ask for it to be configured locally; never ask them to paste it into a public conversation. Do not print or commit credentials.

- Default root: `https://tako.shiroha.tech`; override with `TAKO_BASE_URL`.
- API auth: `Authorization: Bearer $TAKO_API_KEY`.
- `/v1` and `/api/v1` are compatible prefixes for the endpoints below. Native Gemini uses `/v1beta`.
- Helpers require Bash and Python 3 (standard library only; search/System One/usage also use curl). Resolve script paths relative to this skill's directory, not the user's project directory.
- Human installation and first-use instructions: [getting started](docs/getting-started.md).

## Choose the workflow

Read the relevant reference before constructing the request; load other references only when the task needs them.

| Task | Read | Helper / API |
| --- | --- | --- |
| Check token or billing usage | [usage](references/usage.md) | `scripts/tako-usage.sh`; read-only `GET /api/usage/token/` or billing endpoints |
| Search and cite sources | [search](references/search.md) | `scripts/tako-search.sh`; `POST /v1/search` |
| Generate an image | [images](references/images.md) | `scripts/tako-image.sh generate`; `POST /v1/images/generations` |
| Edit one reference image | [images](references/images.md) | `scripts/tako-image.sh edit`; `POST /v1/images/edits` or native Gemini |
| Edit or combine multiple references | [multi-reference recipe](references/images.md#直接调用多张参考图) | Direct JSON `images[].image_url`; the helper takes one image |
| Generate a video (text-to-video or image-to-video) | [video](references/video.md) | `scripts/tako-video.sh generate`; `POST /v1/videos/generations` then poll `GET /v1/videos/{id}` |
| First/last-frame interpolation or multi-reference consistency | [video](references/video.md) | `generate --image --last-frame`; `--ref-image` repeatable, cite `@image0`/`@image1` in the prompt |
| Edit or extend an existing MP4 | [video](references/video.md) | `generate --edit-video` → `POST /v1/videos/edits`; `generate --extend-video` (2–10s) → `POST /v1/videos/extensions` |
| Synthesize speech (default Bingtang), emotion instruct, or zero-shot voice clone | [audio](references/audio.md) | `scripts/tako-audio.sh tts`; `POST /v1/audio/speech` |
| Transcribe speech / audio to text (ASR) | [audio](references/audio.md) | `scripts/tako-audio.sh asr`; `POST /v1/audio/transcriptions` |
| Consult a second model for architecture/code critique | [consult](references/consult.md) | `scripts/tako-consult.sh`; `POST /v1/chat/completions` (`gpt-6.2-sol`) |
| Classify, route, score or judge urgency | [System One](references/systemone.md) | `scripts/tako-systemone.sh` for one Noul; direct `POST /v1/systemone` for other question types |

Use `scripts/tako-consult.sh` when you need a second frontier model to challenge assumptions, inspect concurrency/edge cases, or review code; use `System One` (`jev-latest`) for deterministic `Choice`/`Score`/`Noul` schema decisions. Do not substitute chat-completions for search or System One. `jev-latest` is a decision model, not a chat model; `/v1/models` discovery is not guaranteed to list it.

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

- `grok-imagine-video-1.5` is the only video model; the helper always submits it and maps the legacy name `grok-imagine-video` to it. Default `480p`, 5 seconds; `1080p` is available. Text-to-video and image-to-video are both supported; the reference image is optional. Duration is an integer 1–15 seconds for generation/editing and 2–10 seconds for extension.
- Advanced inputs on `generate`: `--last-frame` locks the last frame (with `--image` it interpolates between the two frames and the prompt becomes optional); repeatable `--ref-image` keeps characters/products consistent across `@imageN` prompt citations; `--edit-video` rewrites an existing MP4 by prompt via `/v1/videos/edits`; `--extend-video` continues an MP4 from its last frame via `/v1/videos/extensions`. Edit and extend take a local MP4 ≤20MB or a URL, are mutually exclusive, and combine only with a prompt.
- Video tasks are asynchronous: `generate` submits, polls until `SUCCESS`/`done`, then downloads the MP4 from `/v1/videos/{id}/content`. A finished MP4 is the only finished artifact — a 200 or a `SUCCESS` status alone is not a delivered video.
- The submitted response is saved with `--out` before polling, so a timed-out or failed poll can be resumed with `scripts/tako-video.sh status <task_id>` instead of paying for a new submission.

```bash
./scripts/tako-video.sh generate "a coral ceramic mug slowly rotating, product shot" \
  --duration 5 --resolution 480p --out task.json --save-video output/mug.mp4
```

## Audio: defaults and input boundaries

- `tts <text>` calls `POST /v1/audio/speech` with default `--model mimo-v2.5-tts`, `--voice 冰糖`, `--format mp3` (`mp3|wav|opus`), optional `--speed`, optional `--instructions`, optional `--voice-sample`, required `--save-audio`, and optional `--out`.
- When `--model` is omitted, `--voice-sample` auto-switches to `mimo-v2.5-tts-voiceclone` (local file ≤ 10,485,760 bytes encoded as `data:<audio-mime>;base64,...` in `voice`), and non-empty `--instructions` auto-switches to `mimo-v2.5-tts-instruct`. Explicit `--model` is always preserved.
- `asr <audio_file>` calls `POST /v1/audio/transcriptions` (multipart `file` + `model`, default `speech_asr`, optional `--language` / `--prompt` / `--out`) and prints the recognized `text`.

```bash
./scripts/tako-audio.sh tts "你好，这是冰糖语音演示。" \
  --save-audio output/bingtang.mp3 --out output/bingtang.json
```

## External consultation: defaults and boundaries

- `tako-consult.sh "<question>"` calls `POST /v1/chat/completions` (`stream: false`, default `--model gpt-6.2-sol`) with an independent senior architecture/code advisor system prompt.
- Supports `--context`, `--context-file`, `--focus`, `--model`, and `--out` (refuses overwrites). Never embed `TAKO_API_KEY` or production secrets inside `--context` or `--context-file`.

```bash
./scripts/tako-consult.sh "并发回调到达时如何避免状态回退？" \
  --context-file src/state_machine.py --focus "幂等与单调锁" --out output/consult.json
```

## Deliver and recover

- Search: cite `results[].url` when present. An empty results array can accompany a valid `answer`; do not invent citations.
- Images: preserve a successful response with `--out`, save/decode actual bytes, report the emitted path and inspect the image. A 200 or base64 string alone is not a finished image artifact. Saving follows actual PNG/JPEG/WebP extension and refuses overwrites.
- Audio: `--save-audio` and `--out` refuse overwrites. `tako-audio.sh tts` validates HTTP 2xx, non-empty bytes, and non-JSON (`{...`) payloads before atomically writing `--save-audio`; HTTP errors or JSON errors must exit non-zero without writing corrupt files. Deliver the saved audio path; for `asr`, deliver the transcribed `text`.
- Consult: deliver the advisor reply (`choices[0].message.content`) and optional `--out` path; distinguish open-ended consultation (`tako-consult.sh`) from structured System One judgments (`tako-systemone.sh`).
- System One: use `model=jev-latest` by default and read `answers`; a returned versioned model id is valid. Keep question types and criteria in the reference's schema.
- Usage: when the user asks about remaining quota, run the read-only usage helper before a paid operation. Distinguish current-token quota from account billing windows; never add the two values together.
- HTTP failures: inspect status and response. Search/System One curl helpers can exit zero on HTTP errors; process status alone is insufficient. `401/403` suggests Key/access, billing errors suggest account/subscription quota, `422` suggests malformed questions.
- Paid calls (images, video, audio): no automatic retries. On timeout, rate limits or saving failures, inspect usage and any saved response before deciding whether to repeat the request. Reuse a successful response to recover an image/video instead of regenerating.
- Video: per-second billing makes blind resubmission costlier. On poll timeout or failure, reuse the saved task JSON with `status`/`--task-json`; only resubmit after confirming the task cannot be recovered.
- Send the Tako Key only to the configured API root, never to image or video CDNs. Do not follow API redirects that could forward credentials.

## Unsupported or unverified workflows

Do not use this skill for image task polling, async/batch image APIs or `/v1/images/variations`. Do not assume masks, transparency, exact multi-reference preservation or every size/quality combination works across models.

Image behavior above was verified on 2026-10-04. Grok video generation was added to the API on 2026-11-16. Audio (Bingtang TTS/instruct/voiceclone/ASR) and external consultation (`gpt-6.2-sol`) helpers follow the active Tako gateway contract. Search and System One references describe the existing contract and earlier checks. Troubleshooting: [common questions](docs/troubleshooting.md).
