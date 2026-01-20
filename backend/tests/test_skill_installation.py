import json
from pathlib import Path


def test_required_skills_installed() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    required_file = repo_root / "skills" / "required-skills.txt"

    assert required_file.exists(), "Missing skills/required-skills.txt"

    missing = []
    for line in required_file.read_text(encoding="utf-8").splitlines():
        skill = line.strip()
        if not skill or skill.startswith("#"):
            continue

        skill_path = repo_root / "skills" / skill / "SKILL.md"
        if not skill_path.exists():
            missing.append(skill)

    assert not missing, f"Missing required skills: {', '.join(missing)}"


def test_ai_research_skills_manifest() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    manifest_path = repo_root / "skills" / "ai-research-skills.manifest.json"

    assert manifest_path.exists(), "Missing ai-research-skills manifest. Run install script."

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    installed = manifest.get("installed", [])
    expected_count = manifest.get("installed_count")

    assert installed, "ai-research-skills manifest has no installed entries."
    if expected_count is not None:
        assert expected_count == len(installed)

    missing = []
    for entry in installed:
        dest = entry.get("dest")
        if not dest:
            missing.append("<missing-dest>")
            continue
        skill_path = repo_root / "skills" / dest / "SKILL.md"
        if not skill_path.exists():
            missing.append(dest)

    assert not missing, f"Missing ai-research skills: {', '.join(missing)}"
