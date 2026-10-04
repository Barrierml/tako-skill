---
name: tako-skill
description: Tako skill for billed web search, images, and System One decisions (POST /v1/systemone). Use when the user asks to search, generate/edit images, or make structured Choice/Score/Noul judgments through Tako.
---

# Tako Skill

Call Tako for web search, images, and System One structured decisions. One public host, one user token.

This repository was renamed from `Barrierml/agent-skills`. Old URLs 301 here. If `bunx skills add Barrierml/agent-skills` still points at the old name, use `Barrierml/tako-skill`.

Do not invent other hosts, paths, or auth schemes. Do not write the API key into this skill, a repo, a screenshot, or a chat log.

## Setup

```bash
export TAKO_BASE_URL="${TAKO_BASE_URL:-https://tako.shiroha.tech}"
export TAKO_API_KEY="YOUR_COMPLETE_TAKO_USER_KEY"   # copy the full console value; preserve its prefix
```

Auth on every call:

```text
Authorization: Bearer $TAKO_API_KEY
```

Compatible prefixes: `/v1`, `/api/v1`.

Helpers in this skill's `scripts/` directory:

```bash
./scripts/tako-search.sh "capital of Japan"
./scripts/tako-image.sh generate "a tiny red apple on a white table"
./scripts/tako-systemone.sh "hello" "Is this a greeting?"
```

## When to use which path

| User intent | Path |
|---|---|
| Search the web, cite sources | `POST /v1/search` |
| Generate or edit a picture | `POST /v1/images/generations` or `/v1/images/edits` |
| Classify, route, score, judge urgency | `POST /v1/systemone` with `jev-latest` |
| Write prose, code, or chat | Use a chat model. Do not use Jev to generate text |

`jev-*` is hidden from the plaza and from public `GET /v1/models`. Discover it from this skill, not from a model picker.

## Recorded checks

Image checks were refreshed on 2026-10-04. Search and System One notes describe the existing contract and earlier checks; they were not re-tested in this image review.

| Capability | Path | Production check |
|---|---|---|
| Web search | `POST /v1/search` | HTTP 200. Default/kab returns sources; `provider=groq` may return only `answer` |
| Image generate | `POST /v1/images/generations` | HTTP 200, `gpt-image-2`, `b64_json` |
| Image edit | `POST /v1/images/edits` | HTTP 200, multipart `image` + `prompt` |
| Structured decision | `POST /v1/systemone` | Contract is TypeSafe System One. Default `jev-latest`. Not chat |

Not in this skill until a live request succeeds:

- Speech ASR / TTS (`/v1/audio/*`) — Xiaomi path is not e2e-green
- Video (`/v1/videos`) — no available channel for `sora-2`

Do not invent brand ability names like `kab_search`.

## 1. Web search

`POST $TAKO_BASE_URL/v1/search`

```json
{
  "query": "capital of Japan",
  "count": 3
}
```

| Field | Required | Notes |
|---|---|---|
| `query` | yes | Non-empty string |
| `provider` | no | Family filter only: `kab`, `groq`, `grok`, `grok_x`. Omit uses channel priority/weight |
| `count` | no | Default 5, max 20 |

`200` example (kab):

```json
{
  "query": "capital of Japan",
  "provider": "kab",
  "answer": "Search results for: capital of Japan\n\n1. Capital of Japan\nhttps://en.wikipedia.org/wiki/Capital_of_Japan\n...",
  "results": [
    {"title": "Capital of Japan", "url": "https://en.wikipedia.org/wiki/Capital_of_Japan", "snippet": "..."}
  ]
}
```

Rules:

- Empty `results` can still be success. Groq short questions often return only `answer`.
- Prefer citing `results[].url` when present.

## 2. Images

Read [references/images.md](references/images.md) for model selection, user examples, response decoding and limitations. It includes actual product photography, 3D illustration, forest photography and a mug-color edit comparison, each with the full prompt and command. Preserve explicit edit invariants when adapting these examples. Users can also try these presets on the [Tako Playground](https://tako.shiroha.tech/playground) image tab: choosing a preset fills inputs without generating; the edit preset loads its reference and generation presets clear any old reference. An explicit Generate action is still required. The live image checks below are dated **2026-10-04**; visibility still depends on the user's token.

- Default: `gpt-image-2`. GPT `gpt-image-2.5-flare` and `gpt-image-2.5-sunburst` also passed generation and multipart editing.
- Gemini `gemini-3.1-flash-image` / `gemini-3-pro-image`: the helper uses native `/v1beta/models/{model}:generateContent` with `inlineData`. Tako fixed the Images compatibility edit path in `tako-20261004-1212`; both models passed JSON and multipart reference editing with standard `data[].b64_json` responses. The reference-loss/wrong-response defect applies to the older `tako-20261002-1433` build.
- Grok `grok-imagine-image-quality`: request `response_format=b64_json`. Its default CDN URL download failed in the verification environment; do not claim a downloadable artifact based only on HTTP 200.
- `./scripts/tako-image.sh` selects the native Gemini path automatically, requests base64 on GPT/Grok (JSON edits for Grok; current upstream multipart conversion drops response_format), and reports HTTP failures with a nonzero exit. It does not automatically retry paid requests.
- Multiple references: use the [multi-reference recipe](references/images.md#直接调用多张参考图) with `/v1/images/edits` JSON `images[].image_url`. Two distinct references were jointly used successfully by `gpt-image-2`, `gemini-3.1-flash-image` and `grok-imagine-image-quality`. Grok's current upstream limits edit sources to three; GPT/Gemini maximum counts and the other models were not tested here. The helper and Playground each accept one reference; do not silently drop additional user images or pass multiple filenames to the single-image helper.

```bash
./scripts/tako-image.sh generate "a tiny red apple on a white table" \
  --out response.json --save-image output/apple.png
./scripts/tako-image.sh edit output/apple.png "change only the apple to green; preserve everything else" \
  --model gemini-3.1-flash-image --out edited.json --save-image output/edited.png
```

`--out` writes JSON; `--save-image` writes image bytes with their actual extension. Report the emitted path, open the file to verify it, and for edits compare it against the reference. Keep a successful response if image saving fails; do not regenerate solely to retry a download. Never attach the Tako key to a CDN request.

Do not poll `/v1/images/tasks/{id}` or call `/v1/images/variations`. Do not silently change the user's chosen model. Masks, multi-reference preservation, transparency and advanced output settings have not been validated across every model.

## 3. System One decisions

`POST $TAKO_BASE_URL/v1/systemone`

Read this section before calling Jev.

- Judging, routing, scoring, urgency → `/v1/systemone`
- Writing articles, writing code, chatting → keep using a chat model
- Default `model`: `jev-latest`
- Do not wrap this as `/v1/chat/completions`
- Do not print the API key
- English state text works best
- Success `model` may be a versioned id such as `jev-1.13.0`. Read `answers`

Minimal Noul:

```bash
curl -sS "$TAKO_BASE_URL/v1/systemone" \
  -H "Authorization: Bearer $TAKO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"state":"hello","model":"jev-latest","questions":{"greeting":{"type":"noul","instructions":"Is this a greeting?"}}}'
```

Helper:

```bash
./scripts/tako-systemone.sh "hello" "Is this a greeting?"
```

`questions` values are `choice`, `score`, or `noul`. `state` may be a string or a JSON object.

Compatible prefix: `$TAKO_BASE_URL/api/v1/systemone`.

For Choice/Score/Noul request examples, read the System One section of the [Tako integration guide](https://tako.shiroha.tech/docs/integrations/tako-skill). The shell helper sends one Noul question; use direct JSON for Choice/Score or multiple questions.

Official TypeSafe SDKs: set `baseURL` / `TYPESAFE_BASE_URL` to `$TAKO_BASE_URL` (no `/v1`) and use the Tako token. `systemOne()` works. Tako `GET /v1/models` does not list `jev-*`, so SDK `models.list()` is not guaranteed.

## Claude Code

Install once, then put the key in the environment of the Claude Code process:

```bash
bunx skills add Barrierml/tako-skill -g -y
export TAKO_API_KEY="YOUR_COMPLETE_TAKO_USER_KEY"
export TAKO_BASE_URL="https://tako.shiroha.tech"
```

Or clone into the project Claude reads:

```bash
git clone https://github.com/Barrierml/tako-skill.git \
  .claude/skills/tako-skill
```

Prompt the model with a concrete task, not a generic “use tools”:

```text
Use the tako-skill skill.
Search Tako for "capital of Japan" and cite the source URLs.
Then generate a simple photo of a tiny red apple on a white table with gpt-image-2.
If I ask to classify or score, POST /v1/systemone with model jev-latest.
Do not wrap systemone as chat. Do not call /v1/videos. Do not print TAKO_API_KEY.
```

Claude Code should read `SKILL.md` and run the curl/helpers itself.

## Codex

Codex does not auto-load Claude skill folders. Give it the contract plus a prompt:

```bash
export TAKO_API_KEY="YOUR_COMPLETE_TAKO_USER_KEY"
export TAKO_BASE_URL="https://tako.shiroha.tech"
```

```text
Follow https://github.com/Barrierml/tako-skill/blob/main/SKILL.md
or the local clone of that repo.

Search POST $TAKO_BASE_URL/v1/search with query "capital of Japan".
If you need an image, POST /v1/images/generations with model gpt-image-2.
If you need a structured Choice/Score/Noul judgment, POST /v1/systemone with model jev-latest.

Do not call video endpoints.
Keep the API key in the Authorization header only.
```

If you already use `tako` to launch Codex, still export `TAKO_API_KEY` in that same shell. The Tako chat key and this skill key are the same user token.

## Workflow

1. Confirm `$TAKO_API_KEY`. If missing, stop and ask.
2. Search for facts. Image only when the user asked for a picture.
3. Classify / score / route with `/v1/systemone`. Do not use Jev to write text.
4. Prefer helper scripts when they exist; otherwise curl the paths above.
5. `401/403`: token invalid or no access. `402`: billing. `422`: malformed questions. Inspect the response as well as the process exit code: search/System One curl helpers can exit zero on HTTP errors. For image errors/timeouts/429, inspect usage and any saved response before deciding whether to repeat a paid request; do not retry automatically. For other calls, follow the rate-limit response.
6. Never print the full API key.

## Do not

- Do not send keys to any host other than `$TAKO_BASE_URL`.
- Do not use chat-completions as a substitute for `/v1/search` or `/v1/systemone`.
- Do not poll image task URLs on Tako.
- Do not hardcode channel IDs.
- Do not treat `jev-*` as a chat model.
- Do not document or call video from this skill until that path returns 200 on a real token.
