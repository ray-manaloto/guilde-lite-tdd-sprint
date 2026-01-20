#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST_PATH="${ROOT_DIR}/skills/ai-research-skills.manifest.json"

if [[ ! -f "${MANIFEST_PATH}" ]]; then
  echo "Missing manifest: ${MANIFEST_PATH}" >&2
  echo "Run scripts/install-ai-research-skills.sh first." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to validate AI research skills." >&2
  exit 1
fi

ROOT_DIR="${ROOT_DIR}" MANIFEST_PATH="${MANIFEST_PATH}" python3 - <<'PY'
import json
import os
from pathlib import Path

root_dir = Path(os.environ["ROOT_DIR"]).resolve()
manifest_path = Path(os.environ["MANIFEST_PATH"]).resolve()

with manifest_path.open("r", encoding="utf-8") as f:
    manifest = json.load(f)

installed = manifest.get("installed", [])
missing = []
for entry in installed:
    dest = entry.get("dest")
    if not dest:
        missing.append("<missing-dest>")
        continue
    skill_path = root_dir / "skills" / dest / "SKILL.md"
    if not skill_path.exists():
        missing.append(dest)

expected = manifest.get("installed_count")
actual = len(installed)

if missing:
    raise SystemExit("Missing SKILL.md for: " + ", ".join(sorted(set(missing))))

if expected is not None and expected != actual:
    raise SystemExit(f"Manifest count mismatch: expected {expected}, got {actual}")

print(f"Validated {actual} installed AI research skills.")
PY