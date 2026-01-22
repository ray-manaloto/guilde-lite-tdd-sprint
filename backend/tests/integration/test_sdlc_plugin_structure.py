"""Tests for SDLC Orchestration Plugin Structure Validation.

This module validates that the SDLC orchestration plugin follows Claude Code
plugin conventions and has all required components properly configured.

Tests cover:
1. Plugin manifest (plugin.json) validation
2. Agent file structure and frontmatter
3. Command file structure and frontmatter
4. Skill file structure
5. Hooks configuration
6. Cross-reference validation (agents referenced in commands exist)
"""

import json
import re
from pathlib import Path

import pytest
import yaml

# Plugin root directory
# Plugin root: backend/tests/integration -> backend/tests -> backend -> project_root
PLUGIN_ROOT = Path(__file__).parent.parent.parent.parent / ".claude/plugins/sdlc-orchestration"


class TestPluginManifest:
    """Tests for plugin.json manifest validation."""

    @pytest.fixture
    def plugin_json(self) -> dict:
        """Load the plugin.json manifest."""
        manifest_path = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
        assert manifest_path.exists(), f"Plugin manifest not found at {manifest_path}"
        return json.loads(manifest_path.read_text())

    def test_plugin_json_exists(self):
        """Verify plugin.json exists in correct location."""
        manifest_path = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
        assert manifest_path.exists(), "plugin.json must exist at .claude-plugin/plugin.json"

    def test_plugin_has_required_fields(self, plugin_json):
        """Verify plugin.json has all required fields."""
        required_fields = ["name", "version", "description"]
        for field in required_fields:
            assert field in plugin_json, f"plugin.json missing required field: {field}"

    def test_plugin_name_is_kebab_case(self, plugin_json):
        """Verify plugin name follows kebab-case convention."""
        name = plugin_json.get("name", "")
        assert re.match(r"^[a-z][a-z0-9-]*$", name), f"Plugin name '{name}' must be kebab-case"

    def test_plugin_version_is_semver(self, plugin_json):
        """Verify plugin version follows semver format."""
        version = plugin_json.get("version", "")
        assert re.match(r"^\d+\.\d+\.\d+$", version), f"Version '{version}' must be semver (e.g., 1.0.0)"

    def test_plugin_author_is_object(self, plugin_json):
        """Verify author is an object, not a string."""
        if "author" in plugin_json:
            assert isinstance(plugin_json["author"], dict), "author must be an object {name: ...}"
            assert "name" in plugin_json["author"], "author object must have 'name' field"

    def test_plugin_keywords_is_array(self, plugin_json):
        """Verify keywords is an array if present."""
        if "keywords" in plugin_json:
            assert isinstance(plugin_json["keywords"], list), "keywords must be an array"

    def test_plugin_has_no_deprecated_fields(self, plugin_json):
        """Verify plugin.json doesn't have deprecated fields."""
        deprecated_fields = ["agents", "skills", "slashCommands", "categories"]
        for field in deprecated_fields:
            assert field not in plugin_json, f"plugin.json contains deprecated field: {field}"


class TestAgentFiles:
    """Tests for agent file structure and frontmatter validation."""

    @pytest.fixture
    def agent_files(self) -> list[Path]:
        """Get all agent markdown files."""
        agents_dir = PLUGIN_ROOT / "agents"
        if not agents_dir.exists():
            return []
        return list(agents_dir.glob("*.md"))

    @pytest.fixture
    def expected_agents(self) -> list[str]:
        """List of expected agent names based on SDLC phases."""
        return [
            # Phase 1: Requirements
            "ceo-stakeholder",
            "business-analyst",
            "research-scientist",
            # Phase 2: Design
            "software-architect",
            "data-scientist",
            "network-engineer",
            # Phase 3: Implementation
            "staff-engineer",
            "senior-engineer",
            "junior-engineer",
            "devops-engineer",
            # Phase 4: Quality
            "qa-automation",
            "code-reviewer",
            "performance-engineer",
            # Phase 5: Release
            "cicd-engineer",
            "canary-user",
            "documentation-engineer",
        ]

    def test_agents_directory_exists(self):
        """Verify agents directory exists."""
        agents_dir = PLUGIN_ROOT / "agents"
        assert agents_dir.exists(), "agents/ directory must exist"

    def test_all_expected_agents_exist(self, agent_files, expected_agents):
        """Verify all expected SDLC agents exist."""
        existing_names = [f.stem for f in agent_files]
        for agent in expected_agents:
            assert agent in existing_names, f"Missing expected agent: {agent}"

    def test_agent_files_have_frontmatter(self, agent_files):
        """Verify all agent files start with YAML frontmatter."""
        for agent_file in agent_files:
            content = agent_file.read_text()
            assert content.startswith("---"), f"Agent {agent_file.name} must start with '---' frontmatter"
            # Find closing frontmatter
            second_delimiter = content.find("---", 3)
            assert second_delimiter > 0, f"Agent {agent_file.name} missing closing '---' for frontmatter"

    def test_agent_frontmatter_has_required_fields(self, agent_files):
        """Verify agent frontmatter has required fields.

        Note: Agent description fields may contain multiline content with
        <example> blocks that don't parse as strict YAML. We check for
        the field presence using regex if YAML parsing fails.
        """
        required_fields = ["name", "description"]

        for agent_file in agent_files:
            content = agent_file.read_text()
            # Extract frontmatter
            if content.startswith("---"):
                end = content.find("---", 3)
                if end > 0:
                    frontmatter_text = content[3:end].strip()
                    try:
                        frontmatter = yaml.safe_load(frontmatter_text)
                        for field in required_fields:
                            assert field in frontmatter, (
                                f"Agent {agent_file.name} missing required frontmatter field: {field}"
                            )
                    except yaml.YAMLError:
                        # Fallback: check for field presence using regex
                        # (handles multiline descriptions with <example> blocks)
                        for field in required_fields:
                            pattern = rf"^{field}:"
                            assert re.search(pattern, frontmatter_text, re.MULTILINE), (
                                f"Agent {agent_file.name} missing required frontmatter field: {field}"
                            )

    def test_agent_has_example_blocks(self, agent_files):
        """Verify agents have <example> blocks in description."""
        for agent_file in agent_files:
            content = agent_file.read_text()
            # Extract frontmatter description
            if content.startswith("---"):
                end = content.find("---", 3)
                if end > 0:
                    frontmatter_text = content[3:end].strip()
                    # Check for example blocks
                    assert "<example>" in frontmatter_text, (
                        f"Agent {agent_file.name} missing <example> block in description"
                    )
                    assert "</example>" in frontmatter_text, (
                        f"Agent {agent_file.name} missing </example> closing tag"
                    )

    def test_agent_names_match_filenames(self, agent_files):
        """Verify agent name in frontmatter matches filename."""
        for agent_file in agent_files:
            content = agent_file.read_text()
            if content.startswith("---"):
                end = content.find("---", 3)
                if end > 0:
                    frontmatter_text = content[3:end].strip()
                    try:
                        frontmatter = yaml.safe_load(frontmatter_text)
                        name = frontmatter.get("name", "")
                        expected_name = agent_file.stem
                        assert name == expected_name, (
                            f"Agent {agent_file.name}: frontmatter name '{name}' "
                            f"doesn't match filename '{expected_name}'"
                        )
                    except yaml.YAMLError:
                        pass  # Already tested in previous test


class TestCommandFiles:
    """Tests for command file structure and frontmatter validation."""

    @pytest.fixture
    def command_files(self) -> list[Path]:
        """Get all command markdown files."""
        commands_dir = PLUGIN_ROOT / "commands"
        if not commands_dir.exists():
            return []
        return list(commands_dir.glob("*.md"))

    @pytest.fixture
    def expected_commands(self) -> list[str]:
        """List of expected command names."""
        return ["full-feature", "research", "phase", "role"]

    def test_commands_directory_exists(self):
        """Verify commands directory exists."""
        commands_dir = PLUGIN_ROOT / "commands"
        assert commands_dir.exists(), "commands/ directory must exist"

    def test_all_expected_commands_exist(self, command_files, expected_commands):
        """Verify all expected commands exist."""
        existing_names = [f.stem for f in command_files]
        for cmd in expected_commands:
            assert cmd in existing_names, f"Missing expected command: {cmd}"

    def test_command_files_have_frontmatter(self, command_files):
        """Verify all command files start with YAML frontmatter."""
        for cmd_file in command_files:
            content = cmd_file.read_text()
            assert content.startswith("---"), f"Command {cmd_file.name} must start with '---' frontmatter"

    def test_command_frontmatter_has_required_fields(self, command_files):
        """Verify command frontmatter has required fields."""
        required_fields = ["name", "description"]

        for cmd_file in command_files:
            content = cmd_file.read_text()
            if content.startswith("---"):
                end = content.find("---", 3)
                if end > 0:
                    frontmatter_text = content[3:end].strip()
                    try:
                        frontmatter = yaml.safe_load(frontmatter_text)
                        for field in required_fields:
                            assert field in frontmatter, (
                                f"Command {cmd_file.name} missing required frontmatter field: {field}"
                            )
                    except yaml.YAMLError as e:
                        pytest.fail(f"Command {cmd_file.name} has invalid YAML frontmatter: {e}")


class TestSkillFiles:
    """Tests for skill file structure validation."""

    def test_skills_directory_exists(self):
        """Verify skills directory exists if any skills are defined."""
        skills_dir = PLUGIN_ROOT / "skills"
        # Skills are optional, but if directory exists, validate structure
        if skills_dir.exists():
            skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
            assert len(skill_dirs) > 0, "skills/ directory exists but contains no skills"

    def test_skill_has_skill_md(self):
        """Verify each skill directory has SKILL.md."""
        skills_dir = PLUGIN_ROOT / "skills"
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir():
                    skill_md = skill_dir / "SKILL.md"
                    assert skill_md.exists(), f"Skill {skill_dir.name} missing SKILL.md"

    def test_skill_md_has_frontmatter(self):
        """Verify SKILL.md files have frontmatter."""
        skills_dir = PLUGIN_ROOT / "skills"
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir():
                    skill_md = skill_dir / "SKILL.md"
                    if skill_md.exists():
                        content = skill_md.read_text()
                        assert content.startswith("---"), (
                            f"Skill {skill_dir.name}/SKILL.md must start with frontmatter"
                        )


class TestHooksConfiguration:
    """Tests for hooks.json configuration validation."""

    @pytest.fixture
    def hooks_json(self) -> dict | None:
        """Load hooks.json if it exists."""
        hooks_path = PLUGIN_ROOT / "hooks" / "hooks.json"
        if not hooks_path.exists():
            return None
        return json.loads(hooks_path.read_text())

    def test_hooks_json_is_valid(self, hooks_json):
        """Verify hooks.json is valid JSON if it exists."""
        if hooks_json is not None:
            assert isinstance(hooks_json, dict), "hooks.json must be a JSON object"

    def test_hooks_have_valid_event_names(self, hooks_json):
        """Verify hooks use valid event names."""
        valid_events = [
            "PreToolUse",
            "PostToolUse",
            "UserPromptSubmit",
            "AgentTurnStart",
            "AgentTurnEnd",
            "SessionStart",
        ]
        if hooks_json:
            for event in hooks_json.keys():
                assert event in valid_events, f"Invalid hook event: {event}"

    def test_hooks_have_valid_structure(self, hooks_json):
        """Verify hooks have correct structure."""
        if hooks_json:
            for event, hooks_list in hooks_json.items():
                assert isinstance(hooks_list, list), f"Hook {event} must be an array"
                for hook in hooks_list:
                    # Each hook should have matcher and hooks or type
                    assert isinstance(hook, dict), f"Hook in {event} must be an object"


class TestCrossReferences:
    """Tests for validating cross-references between components."""

    @pytest.fixture
    def all_agent_names(self) -> set[str]:
        """Get all defined agent names."""
        agents_dir = PLUGIN_ROOT / "agents"
        if not agents_dir.exists():
            return set()
        return {f.stem for f in agents_dir.glob("*.md")}

    def test_commands_reference_valid_agents(self, all_agent_names):
        """Verify commands only reference agents that exist."""
        commands_dir = PLUGIN_ROOT / "commands"
        if not commands_dir.exists():
            return

        # Pattern to find agent references like sdlc-orchestration:agent-name
        agent_ref_pattern = re.compile(r'sdlc-orchestration:([a-z-]+)')

        for cmd_file in commands_dir.glob("*.md"):
            content = cmd_file.read_text()
            references = agent_ref_pattern.findall(content)

            for ref in references:
                # Some references might be to commands, not agents
                if ref not in ["full-feature", "research", "phase", "role"]:
                    assert ref in all_agent_names, (
                        f"Command {cmd_file.name} references unknown agent: {ref}"
                    )

    def test_full_feature_references_all_phase_agents(self, all_agent_names):
        """Verify full-feature command references agents for all phases."""
        full_feature_path = PLUGIN_ROOT / "commands" / "full-feature.md"
        if not full_feature_path.exists():
            pytest.skip("full-feature.md not found")

        content = full_feature_path.read_text()

        # Essential agents that should be referenced
        essential_agents = [
            "ceo-stakeholder",
            "business-analyst",
            "software-architect",
            "staff-engineer",
            "qa-automation",
            "code-reviewer",
        ]

        for agent in essential_agents:
            assert agent in content, (
                f"full-feature.md should reference essential agent: {agent}"
            )


class TestPluginDocumentation:
    """Tests for plugin documentation completeness."""

    def test_readme_exists(self):
        """Verify README.md exists at plugin root."""
        readme = PLUGIN_ROOT / "README.md"
        assert readme.exists(), "README.md must exist at plugin root"

    def test_readme_has_content(self):
        """Verify README.md has substantial content."""
        readme = PLUGIN_ROOT / "README.md"
        if readme.exists():
            content = readme.read_text()
            assert len(content) > 100, "README.md should have substantial content"
            assert "# " in content, "README.md should have markdown headers"


# Run as standalone script for quick validation
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
