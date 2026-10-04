# Tako Skill

Public Tako skill for web search, images, and System One structured decisions.

This repository contains the skill definition, guides, examples and helpers. Image saving uses Python 3's standard library; search and System One helpers use curl. It does **not** include API keys, channel IDs, or production credentials.

This repository was renamed from `Barrierml/agent-skills`. GitHub keeps a 301 from the old URL. If `bunx skills add Barrierml/agent-skills` still points at the old name, use:

```bash
bunx skills add Barrierml/tako-skill -g -y
```

## What works today

| Family | Method | Path | Last live check |
|---|---|---|---|
| Web search | `POST` | `/v1/search` | 200; kab returns sources, groq may return only `answer` |
| Image generate | `POST` | `/v1/images/generations` | 200 with `gpt-image-2` |
| Image edit | `POST` | `/v1/images/edits` | 200 with `gpt-image-2` |
| Structured decision | `POST` | `/v1/systemone` | TypeSafe System One contract. Default `jev-latest`. Not listed on plaza or `GET /v1/models` |

Speech and video are **not** part of this skill. Those public paths exist on Tako, but current production e2e is not green (`/v1/audio/*` Xiaomi 400/404, `/v1/videos` no `sora-2` channel).

Default host: `https://tako.shiroha.tech`

Auth: `Authorization: Bearer $TAKO_API_KEY`

## Install

Helpers require Bash, Python 3 and curl; cloning also requires Git. Copy the complete user Key from the Tako console without changing its prefix.

```bash
bunx skills add Barrierml/tako-skill -g -y
```

Or clone into a project:

```bash
git clone https://github.com/Barrierml/tako-skill.git \
  .claude/skills/tako-skill
```

Then set a user token:

```bash
export TAKO_API_KEY="YOUR_COMPLETE_TAKO_USER_KEY"
export TAKO_BASE_URL="https://tako.shiroha.tech"
```

## Claude Code prompt

```text
Use the tako-skill skill.
Search Tako for "capital of Japan" and cite the source URLs.
Then generate a simple photo of a tiny red apple on a white table with gpt-image-2.
If I ask to classify or score, POST /v1/systemone with model jev-latest.
Do not wrap systemone as chat. Do not call /v1/videos. Do not print TAKO_API_KEY.
```

## Codex prompt

```text
Follow https://github.com/Barrierml/tako-skill/blob/main/SKILL.md
Search POST $TAKO_BASE_URL/v1/search with query "capital of Japan".
If you need an image, POST /v1/images/generations with model gpt-image-2.
If you need a structured Choice/Score/Noul judgment, POST /v1/systemone with model jev-latest.
Do not call video endpoints. Keep the API key in the Authorization header only.
```

## Helpers

```bash
./scripts/tako-search.sh "capital of Japan"
./scripts/tako-image.sh generate "a tiny red apple on a white table"
./scripts/tako-systemone.sh "hello" "Is this a greeting?"
```

See [`SKILL.md`](./SKILL.md) for the contract agents should follow.

For complete image examples, model routing and saving results, read [图片生成与改图](./references/images.md). The image helper supports GPT/Grok Images API and native Gemini image generation/editing.

For two or more reference images, use the guide's [direct multi-reference API example](./references/images.md#直接调用多张参考图). Two references passed live checks on GPT Image 2, Gemini Flash Image and Grok Image Quality; the helper and Playground still accept one reference. Grok's current upstream allows at most three; GPT/Gemini maxima were not verified.

## Security

- Put the key in the environment only.
- Do not commit `.env`, tokens, or binary dumps that contain secrets.
- Do not send the key to any host other than `TAKO_BASE_URL`.
