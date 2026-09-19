# Search

Verified HTTP 200 against `https://tako.shiroha.tech/v1/search`.

```bash
export TAKO_API_KEY="cr_..."
./scripts/tako-search.sh "capital of Japan" --count 3
```

Optional family filter:

```bash
./scripts/tako-search.sh "capital of Japan" --provider groq --count 3
```

# Image generate

Verified HTTP 200 against `/v1/images/generations` with `gpt-image-2`.

```bash
./scripts/tako-image.sh generate "a tiny red apple on a white table, simple photo" --model gpt-image-2
```

# Image edit

Verified HTTP 200 against `/v1/images/edits` with `gpt-image-2`.

```bash
./scripts/tako-image.sh edit ./input.png "make the apple green" --model gpt-image-2
```

# System One

Structured Choice / Score / Noul judgment. Default model `jev-latest`. Not listed on plaza or `GET /v1/models`.

```bash
export TAKO_API_KEY="cr_..."
./scripts/tako-systemone.sh "hello" "Is this a greeting?"
```
