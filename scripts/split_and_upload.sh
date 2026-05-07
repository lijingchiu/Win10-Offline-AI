#!/usr/bin/env bash
# split_and_upload.sh
# Splits large GGUF files into <2GB chunks and uploads to GitHub Releases.
# Run on a Mac/Linux machine with internet access.
# Requires: gh CLI authenticated with workflow+repo scope

set -euo pipefail

REPO="lijingchiu/Win10-Offline-AI"
RELEASE_TAG="latest-build"
MODELS_DIR="$(dirname "$0")/../models_download"
CHUNK_SIZE="1800M"   # 1.8 GB — safely under GitHub's 2 GB asset limit

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

command -v gh   >/dev/null || error "gh CLI not found. Install: brew install gh"
command -v split >/dev/null || error "split not found"

info "Repo:    $REPO"
info "Tag:     $RELEASE_TAG"
info "Src dir: $MODELS_DIR"
echo

# Ensure release exists
gh release view "$RELEASE_TAG" --repo "$REPO" >/dev/null 2>&1 || \
  gh release create "$RELEASE_TAG" --repo "$REPO" \
     --title "Win10 離線 AI — 最新版" \
     --notes "Auto-generated release" \
     --draft=false

process_model() {
  local gguf_file="$1"
  local base_name
  base_name="$(basename "$gguf_file")"

  if [[ ! -f "$gguf_file" ]]; then
    warn "File not found: $gguf_file — skipping"
    return
  fi

  local size_bytes
  size_bytes=$(wc -c < "$gguf_file")
  local size_gb
  size_gb=$(python3 -c "print(f'{$size_bytes/1024**3:.2f}')")
  info "Processing: $base_name ($size_gb GB)"

  # Split into chunks
  local split_dir
  split_dir="$(dirname "$gguf_file")/.split_${base_name}"
  mkdir -p "$split_dir"

  info "  Splitting into ${CHUNK_SIZE} chunks..."
  split -b "$CHUNK_SIZE" -d --suffix-length=1 \
        "$gguf_file" "$split_dir/${base_name}.part"

  # Rename to .part1, .part2, ...  (split produces part0, part1, ...)
  local n=1
  for f in "$split_dir/${base_name}.part"?; do
    mv "$f" "$split_dir/${base_name}.part${n}"
    n=$((n+1))
  done

  local total_parts=$((n-1))
  info "  Created $total_parts parts"

  # Upload each part
  for f in "$split_dir/${base_name}.part"*; do
    local part_name
    part_name="$(basename "$f")"
    local part_size
    part_size=$(wc -c < "$f")
    local part_gb
    part_gb=$(python3 -c "print(f'{$part_size/1024**3:.2f}')")

    # Check if asset already exists on this release
    if gh release view "$RELEASE_TAG" --repo "$REPO" --json assets \
         | python3 -c "import sys,json; names=[a['name'] for a in json.load(sys.stdin)['assets']]; exit(0 if '${part_name}' in names else 1)" 2>/dev/null; then
      info "  ✓ Already uploaded: $part_name — skipping"
    else
      info "  ⬆  Uploading: $part_name ($part_gb GB)..."
      gh release upload "$RELEASE_TAG" "$f" \
         --repo "$REPO" \
         --clobber
      info "  ✅ Uploaded: $part_name"
    fi
  done

  info "✅ Done: $base_name → $total_parts parts uploaded"
  echo

  # Cleanup split dir
  rm -rf "$split_dir"
}

# Process both models
process_model "$MODELS_DIR/Qwen3-8B-Q4_K_M.gguf"
process_model "$MODELS_DIR/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"

info "All models uploaded to GitHub Releases."
info "Release URL: https://github.com/$REPO/releases/tag/$RELEASE_TAG"
