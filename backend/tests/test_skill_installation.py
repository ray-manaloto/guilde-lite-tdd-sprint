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
