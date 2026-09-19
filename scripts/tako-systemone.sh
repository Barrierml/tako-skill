#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: tako-systemone.sh <state> [noul-question] [--model jev-latest]

Sends one Noul question to POST /v1/systemone.

Requires TAKO_API_KEY. Optional TAKO_BASE_URL (default https://tako.shiroha.tech).
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 1 ]]; then
  usage
  exit 0
fi

state=""
question="Is this a greeting?"
model="jev-latest"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      model="${2:-jev-latest}"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "unknown flag: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      if [[ -z "$state" ]]; then
        state="$1"
      else
        question="$1"
      fi
      shift
      ;;
  esac
done

if [[ -z "${TAKO_API_KEY:-}" ]]; then
  echo "TAKO_API_KEY is required" >&2
  exit 1
fi

base="${TAKO_BASE_URL:-https://tako.shiroha.tech}"
base="${base%/}"

body=$(python3 - "$state" "$question" "$model" <<'PY'
import json, sys
state, question, model = sys.argv[1], sys.argv[2], sys.argv[3]
print(json.dumps({
    "state": state,
    "model": model,
    "questions": {
        "greeting": {
            "type": "noul",
            "instructions": question,
        }
    },
}, ensure_ascii=False))
PY
)

curl -sS "$base/v1/systemone" \
  -H "Authorization: Bearer ${TAKO_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$body"
echo
