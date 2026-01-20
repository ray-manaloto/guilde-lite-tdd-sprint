#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQUIRED_FILE="${ROOT_DIR}/skills/required-skills.txt"

if [[ ! -f "${REQUIRED_FILE}" ]]; then
  echo "Missing required skills list: ${REQUIRED_FILE}" >&2
  exit 1
fi

missing=()

while IFS= read -r skill; do
  [[ -z "${skill}" ]] && continue
  [[ "${skill}" =~ ^# ]] && continue

  skill_path="${ROOT_DIR}/skills/${skill}/SKILL.md"
  if [[ ! -f "${skill_path}" ]]; then
    missing+=("${skill}")
  fi
done < "${REQUIRED_FILE}"

if (( ${#missing[@]} > 0 )); then
  echo "Missing required skills:" >&2
  printf "  - %s\n" "${missing[@]}" >&2
  exit 1
fi

echo "All required skills are installed."
