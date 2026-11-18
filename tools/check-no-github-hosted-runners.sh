#!/usr/bin/env bash
# Fail if any workflow job uses a GitHub-hosted Ubuntu runs-on (ubuntu-*).
# macOS/Windows hosted runners are separately BLOCKED (no org runners); not covered here.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
wf="$root/.github/workflows"
fail=0
while IFS= read -r -d '' f; do
  if sed 's/#.*//' "$f" | grep -E 'runs-on:[[:space:]]*ubuntu-' >/dev/null; then
    echo "HOSTED_UBUNTU_RUNNER: $f" >&2
    sed 's/#.*//' "$f" | grep -nE 'runs-on:[[:space:]]*ubuntu-' >&2 || true
    fail=1
  fi
done < <(find "$wf" -type f \( -name '*.yml' -o -name '*.yaml' \) -print0 2>/dev/null)
if [[ "$fail" -ne 0 ]]; then
  echo "check-no-github-hosted-runners: FAIL" >&2
  exit 1
fi
echo "check-no-github-hosted-runners: OK"
