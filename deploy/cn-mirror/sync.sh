#!/usr/bin/env bash
set -euo pipefail

# Mirror the public main branch into an atomic, nginx-readable release tree.
# Run on the mirror host; this script never writes to the GitHub repository.
REPO="${TAKO_SKILL_REPO:-Barrierml/tako-skill}"
REF="${TAKO_SKILL_REF:-main}"
ROOT="${TAKO_SKILL_MIRROR_ROOT:-/srv/tako-skill-mirror}"
KEEP_RELEASES="${TAKO_SKILL_KEEP_RELEASES:-3}"

case "$KEEP_RELEASES" in
  ''|*[!0-9]*) echo "TAKO_SKILL_KEEP_RELEASES must be a number" >&2; exit 2 ;;
esac
if (( KEEP_RELEASES < 1 )); then
  echo "TAKO_SKILL_KEEP_RELEASES must be at least 1" >&2
  exit 2
fi

command -v curl >/dev/null || { echo "curl is required" >&2; exit 1; }
command -v tar >/dev/null || { echo "tar is required" >&2; exit 1; }
command -v sha256sum >/dev/null || { echo "sha256sum is required" >&2; exit 1; }

mkdir -p "$ROOT/releases"
exec 9>"$ROOT/.sync.lock"
if ! flock -n 9; then
  echo "another Tako Skill sync is running" >&2
  exit 0
fi

tmp="$(mktemp -d "$ROOT/.incoming.XXXXXX")"
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT

archive="$tmp/source.tar.gz"
archive_url="${TAKO_SKILL_ARCHIVE_URL:-https://codeload.github.com/${REPO}/tar.gz/refs/heads/${REF}}"
curl --fail --location --retry 3 --connect-timeout 10 --max-time 180 \
  "$archive_url" \
  -o "$archive"

tar -xzf "$archive" -C "$tmp"
source_dir="$(find "$tmp" -mindepth 1 -maxdepth 1 -type d -print -quit)"
if [[ -z "$source_dir" || ! -f "$source_dir/README.md" || ! -f "$source_dir/SKILL.md" ]]; then
  echo "archive does not look like a Tako Skill release" >&2
  exit 1
fi

# API lookup is best-effort: the archive remains usable if GitHub API is rate-limited.
commit="unknown"
if response="$(curl --fail --silent --show-error --connect-timeout 10 --max-time 20 \
  "${TAKO_SKILL_COMMIT_URL:-https://api.github.com/repos/${REPO}/commits/${REF}}" 2>/dev/null)"; then
  commit="$(printf '%s' "$response" | sed -n 's/.*"sha": "\([0-9a-f]*\)".*/\1/p' | head -1)"
  [[ -n "$commit" ]] || commit="unknown"
fi
if [[ "$commit" == "unknown" ]]; then
  commit="$(sha256sum "$archive" | cut -d' ' -f1)"
fi

release="$ROOT/releases/$commit"
if [[ -e "$release" ]]; then
  ln -sfn "$release" "$ROOT/current.next"
  mv -f "$ROOT/current.next" "$ROOT/current"
  echo "already mirrored $commit"
else
  mkdir -p "$release"
  cp -a "$source_dir/." "$release/"
  cp "$archive" "$release/tako-skill.tar.gz"
  sha256sum "$release/tako-skill.tar.gz" > "$release/tako-skill.tar.gz.sha256"
  cat > "$release/latest.json" <<JSON
{
  "repository": "https://github.com/${REPO}",
  "ref": "${REF}",
  "commit": "${commit}",
  "archive": "/tako-skill.tar.gz",
  "archive_sha256_file": "/tako-skill.tar.gz.sha256"
}
JSON
  cat > "$release/index.html" <<HTML
<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tako Skill 国内镜像</title>
<style>body{max-width: 50rem;margin:3rem auto;padding:0 1rem;font:16px/1.6 system-ui,sans-serif;color:#202124}a{color:#06c}code{background:#f1f3f4;padding:.1rem .3rem}</style>
<h1>Tako Skill 国内镜像</h1>
<p>此站同步自 <a href="https://github.com/${REPO}">GitHub</a> 的 <code>${REF}</code>，当前提交 <code>${commit}</code>。</p>
<ul>
<li><a href="/README.md">README</a>：给人看的安装与示例</li>
<li><a href="/SKILL.md">SKILL.md</a>：给 AI 助手的入口</li>
<li><a href="/docs/getting-started.md">快速开始</a></li>
<li><a href="/references/images.md">图片与提示词</a></li>
<li><a href="/references/usage.md">用量与额度</a></li>
<li><a href="/tako-skill.tar.gz">下载完整 Skill 压缩包</a>（<a href="/tako-skill.tar.gz.sha256">SHA-256</a>）</li>
</ul>
</html>
HTML
  ln -sfn "$release" "$ROOT/current.next"
  mv -f "$ROOT/current.next" "$ROOT/current"
  echo "mirrored $commit"
fi

# Keep the current release plus the newest historical releases. The mirror
# host is Linux, but this form also keeps the script runnable on macOS during QA.
while IFS= read -r old; do
  [[ -z "$old" || "$old" == "$release" ]] || rm -rf -- "$old"
done < <(ls -dt "$ROOT"/releases/* 2>/dev/null | tail -n +$((KEEP_RELEASES + 1)))
