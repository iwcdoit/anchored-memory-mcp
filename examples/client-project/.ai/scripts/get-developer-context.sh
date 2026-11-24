#!/usr/bin/env bash
set -euo pipefail

json_escape() {
  local val="${1-}"
  val="${val//\\/\\\\}"
  val="${val//\"/\\\"}"
  val="${val//$'\n'/\\n}"
  printf '%s' "$val"
}

if git_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  is_git_repo=true
else
  git_root="$(pwd)"
  is_git_repo=false
fi

remote="$(git -C "$git_root" remote get-url origin 2>/dev/null || true)"
if [[ -n "$remote" ]]; then
  repo="${remote##*/}"
  [[ "$repo" == "$remote" ]] && repo="${remote##*:}"
  repo="${repo%.git}"
  source_kind="origin"
else
  repo="$(basename "$git_root")"
  source_kind="git-root"
fi

branch="$(git -C "$git_root" branch --show-current 2>/dev/null || true)"
commit="$(git -C "$git_root" rev-parse --verify HEAD 2>/dev/null || true)"
dev_name="$(git -C "$git_root" config --get user.name 2>/dev/null || whoami)"
dev_email="$(git -C "$git_root" config --get user.email 2>/dev/null || true)"
now_utc="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

cat <<EOF
{
  "repository": "$(json_escape "$repo")",
  "repository_source": "$source_kind",
  "is_git_repository": $is_git_repo,
  "branch": "$(json_escape "$branch")",
  "commit": "$(json_escape "$commit")",
  "developer_id": "$(json_escape "$dev_name")",
  "developer_email": "$(json_escape "$dev_email")",
  "created_at": "$now_utc"
}
EOF
