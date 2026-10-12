#!/usr/bin/env bash
# Usage: GITHUB_TOKEN=... ./run_agent.sh <owner/repo> <tag>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

IMAGE_NAME="${IMAGE_NAME:-release-scan-subagent}"
CACHE_VOLUME="${CACHE_VOLUME:-clamav_db_cache}"

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <owner/repo> <tag>" >&2
  exit 2
fi
REPO_TARGET="$1"
TAG_TARGET="$2"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "[❌] GITHUB_TOKEN must be set in the environment." >&2
  exit 2
fi

# 1. Ensure the persistent volume for ClamAV definitions exists
docker volume create "$CACHE_VOLUME" > /dev/null

# 2. Build the sub-agent image
echo "[*] Building Sub-Agent Container Image..."
docker build -t "$IMAGE_NAME" "$SCRIPT_DIR"

# 3. Refresh virus definitions in the cached volume (cached copy is used if this fails)
echo "[*] Synchronizing virus definitions..."
docker run --rm \
  -v "$CACHE_VOLUME:/var/lib/clamav" \
  --entrypoint freshclam \
  "$IMAGE_NAME" || echo "[!] freshclam update failed; using cached definitions"

# 4. Run the sub-agent. The token is passed by name so its value never appears in argv.
echo "[*] Orchestrating Sub-Agent Scan Execution..."
set +e
docker run --rm \
  -e GITHUB_TOKEN \
  -v "$CACHE_VOLUME:/var/lib/clamav" \
  "$IMAGE_NAME" --repo "$REPO_TARGET" --tag "$TAG_TARGET"
status=$?
set -e

case $status in
  0) echo "[+] Scan complete: CLEAN" ;;
  1) echo "[!] Scan complete: INFECTED / VERIFY. Review the attached report before publishing." ;;
  *) echo "[❌] Sub-Agent failed with exit code $status" ;;
esac
exit "$status"
