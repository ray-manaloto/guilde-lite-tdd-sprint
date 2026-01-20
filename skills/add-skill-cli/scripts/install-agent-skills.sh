#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SKILL_SOURCE="${SKILL_SOURCE:-vercel-labs/agent-skills}"
AGENT_TARGET="${AGENT_TARGET:-clawdbot}"

default_skills=(react-best-practices web-design-guidelines vercel-deploy-claimable)
skills=("$@")

if [[ ${#skills[@]} -eq 0 ]]; then
  skills=("${default_skills[@]}")
fi

args=()
for skill in "${skills[@]}"; do
  args+=(--skill "${skill}")
done

cd "${ROOT_DIR}"
npx add-skill "${SKILL_SOURCE}" --agent "${AGENT_TARGET}" -y "${args[@]}"
