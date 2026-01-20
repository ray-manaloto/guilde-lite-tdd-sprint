#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SKILL_SOURCE="${SKILL_SOURCE:-vercel-labs/agent-skills}"

cd "${ROOT_DIR}"
npx add-skill "${SKILL_SOURCE}" --list
