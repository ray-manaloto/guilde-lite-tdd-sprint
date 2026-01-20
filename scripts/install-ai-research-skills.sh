#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_URL="https://github.com/zechenzhangAGI/AI-research-SKILLs.git"
REF="main"
FORCE="false"

usage() {
  cat <<'EOF'
Usage: scripts/install-ai-research-skills.sh [--ref <git-ref>] [--force]

Installs the zechenzhangAGI/AI-research-SKILLs marketplace into project-scoped
Codex skills under ./skills.

Options:
  --ref <git-ref>  Git ref to install (default: main)
  --force          Overwrite existing installed skills
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ref)
      REF="$2"
      shift 2
      ;;
    --force)
      FORCE="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
 done

if ! command -v git >/dev/null 2>&1; then
  echo "git is required to install AI research skills." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to install AI research skills." >&2
  exit 1
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

git clone --depth 1 --branch "${REF}" "${REPO_URL}" "${tmpdir}" >/dev/null

marketplace_json="${tmpdir}/.claude-plugin/marketplace.json"
if [[ ! -f "${marketplace_json}" ]]; then
  echo "Missing marketplace.json in ${REPO_URL} at ${REF}." >&2
  exit 1
fi

ROOT_DIR="${ROOT_DIR}" TMPDIR="${tmpdir}" FORCE="${FORCE}" REF="${REF}" python3 - <<'PY'
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

root_dir = Path(os.environ["ROOT_DIR"]).resolve()
tmpdir = Path(os.environ["TMPDIR"]).resolve()
force = os.environ["FORCE"].lower() == "true"
marketplace_path = tmpdir / ".claude-plugin" / "marketplace.json"

with marketplace_path.open("r", encoding="utf-8") as f:
    data = json.load(f)

skills_root = root_dir / "skills"
skills_root.mkdir(parents=True, exist_ok=True)

installed = []
for plugin in data.get("plugins", []):
    plugin_name = plugin.get("name", "unknown")
    for skill_path in plugin.get("skills", []):
        src = (tmpdir / skill_path).resolve()
        skill_dir = src.name
        dest_name = f"ai-research-{plugin_name}-{skill_dir}"
        dest = skills_root / dest_name

        if not src.exists():
            raise SystemExit(f"Missing skill source: {src}")
        if not (src / "SKILL.md").exists():
            raise SystemExit(f"Missing SKILL.md in {src}")
        if dest.exists():
            if not force:
                raise SystemExit(f"Skill already exists: {dest_name} (use --force to overwrite)")
            shutil.rmtree(dest)

        shutil.copytree(src, dest)
        installed.append({
            "plugin": plugin_name,
            "skill": skill_dir,
            "source": str(Path(skill_path)),
            "dest": dest_name,
        })

manifest = {
    "source_repo": "https://github.com/zechenzhangAGI/AI-research-SKILLs",
    "source_ref": os.environ["REF"],
    "marketplace": data.get("name"),
    "version": data.get("metadata", {}).get("version"),
    "installed_at": datetime.now(timezone.utc).isoformat(),
    "installed_count": len(installed),
    "installed": installed,
}

manifest_path = skills_root / "ai-research-skills.manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

marketplace_copy = skills_root / "ai-research-skills.marketplace.json"
marketplace_copy.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

print(f"Installed {len(installed)} skills into {skills_root}")
print(f"Wrote manifest: {manifest_path}")
print(f"Wrote marketplace copy: {marketplace_copy}")
PY
