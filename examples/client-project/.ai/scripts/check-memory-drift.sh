#!/usr/bin/env bash
# Client-side read-time lazy drift check for a retrieved memory note's code anchors.
# Usage: .ai/scripts/check-memory-drift.sh <base_commit> "<comma_separated_paths>" "<comma_separated_symbols>"
set -euo pipefail

base_commit="${1-}"
raw_paths="${2-}"
raw_symbols="${3-}"

git_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
IFS=',' read -r -a paths <<< "$raw_paths"
IFS=',' read -r -a symbols <<< "$raw_symbols"

missing_paths=0
for rel in "${paths[@]}"; do
  rel="$(echo "$rel" | xargs)"
  [[ -z "$rel" ]] && continue
  if [[ ! -f "$git_root/$rel" ]]; then
    echo "DRIFTED: missing file $rel"
    missing_paths=$((missing_paths + 1))
  fi
done

if [[ "$missing_paths" -gt 0 ]]; then
  exit 2
fi

for sym in "${symbols[@]}"; do
  sym="$(echo "$sym" | xargs)"
  [[ -z "$sym" ]] && continue
  IFS='#' read -r -a tokens <<< "$sym"
  found_in_any=false
  for rel in "${paths[@]}"; do
    rel="$(echo "$rel" | xargs)"
    [[ -z "$rel" ]] && continue
    match_all=true
    for tok in "${tokens[@]}"; do
      if ! grep -Fq "$tok" "$git_root/$rel" 2>/dev/null; then
        match_all=false
        break
      fi
    done
    if [[ "$match_all" == true ]]; then
      found_in_any=true
      break
    fi
  done
  if [[ "$found_in_any" == false ]]; then
    echo "DRIFTED: missing symbol $sym"
    exit 2
  fi
done

if [[ -n "$base_commit" ]] && git -C "$git_root" cat-file -e "${base_commit}^{commit}" 2>/dev/null; then
  changed="$(git -C "$git_root" diff --name-only "${base_commit}..HEAD" -- "${paths[@]}" 2>/dev/null || true)"
  if [[ -n "$changed" ]]; then
    echo "MODIFIED_SAFE: files evolved since $base_commit, but all anchored symbols remain intact"
    exit 0
  fi
fi

echo "CLEAN: code anchors match current working tree"
