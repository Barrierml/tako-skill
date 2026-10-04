#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'HELP'
Usage: tako-usage.sh [token|billing]

Reads usage without generating a request.
  token   current API token quota, model limits and expiry (default)
  billing user billing subscription and aggregate usage endpoints

Requires TAKO_API_KEY. Optional TAKO_BASE_URL (default https://tako.shiroha.tech).
The key is sent only to the Tako API root; responses are printed to stdout.
HELP
}

mode="${1:-token}"
if [[ "$mode" == "-h" || "$mode" == "--help" ]]; then
  usage
  exit 0
fi
if [[ "$mode" != "token" && "$mode" != "billing" ]]; then
  echo "unknown mode: $mode" >&2
  usage >&2
  exit 2
fi
if [[ -z "${TAKO_API_KEY:-}" ]]; then
  echo "TAKO_API_KEY is required" >&2
  exit 1
fi

base="${TAKO_BASE_URL:-https://tako.shiroha.tech}"
base="${base%/}"
auth=( -H "Authorization: Bearer ${TAKO_API_KEY}" -H "Accept: application/json" )

if [[ "$mode" == "token" ]]; then
  curl -fsS "${base}/v1/usage/token/" "${auth[@]}"
  echo
  exit 0
fi

tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/tako-usage.XXXXXX")"
trap 'rm -rf "$tmp_dir"' EXIT
curl -fsS "${base}/v1/dashboard/billing/subscription" "${auth[@]}" >"$tmp_dir/subscription.json"
curl -fsS "${base}/v1/dashboard/billing/usage" "${auth[@]}" >"$tmp_dir/usage.json"
python3 - "$tmp_dir/subscription.json" "$tmp_dir/usage.json" <<'PY'
import json
import sys
from pathlib import Path

subscription = json.loads(Path(sys.argv[1]).read_text())
usage = json.loads(Path(sys.argv[2]).read_text())
print(json.dumps({"subscription": subscription, "usage": usage}, ensure_ascii=False, indent=2))
PY
