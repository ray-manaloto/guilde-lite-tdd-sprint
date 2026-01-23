# Research Report: Todolist Sprint Prompt Improvements for Agentic-Browser Testing

## Executive Summary

This research evaluates the feasibility of improving the "todolist - 001" sprint prompt to work reliably with agentic-browser automated integration testing. The analysis identifies **significant gaps** between what the test expects and what the PhaseRunner prompts instruct the AI to produce. The current prompts are too generic and lack explicit instructions for creating the specific package structure the test validates.

**Recommendation**: Modify PhaseRunner prompts to be more prescriptive for multi-file package projects, adding explicit structure requirements and verification criteria. Feasibility is **HIGH** with estimated effort of **S (Small)**.

## Research Question

How can we improve the sprint prompts in PhaseRunner to produce consistent, testable output that passes the `test_agent_browser_todolist.py` integration test?

## Methodology

1. Analyzed `backend/tests/integration/test_agent_browser_todolist.py` to extract test expectations
2. Analyzed `backend/app/runners/phase_runner.py` to understand current prompt structure
3. Compared expected outputs vs. prompt instructions
4. Reviewed evaluator system for validation patterns
5. Researched AI prompt engineering best practices for deterministic outputs

---

## Findings

### Test Expectations (TODOLIST_GOAL)

The test expects the following exact structure:

```
TODOLIST_GOAL = """Create a Python CLI todo list manager with the following requirements:

1. Package structure: todo/ with __init__.py, cli.py, store.py, __main__.py
2. Commands via argparse (no external deps):
   - add TITLE: Add a new task
   - list: Show all tasks
   - done ID: Mark task as done
3. Storage: JSON file at ~/.todo_test.json
4. Run via: python -m todo <command>

Keep it minimal but functional."""
```

**Test Validation Points:**

| Validation | Code Location | Expected |
|------------|---------------|----------|
| Package exists | Line 107-109 | `todo/__init__.py` exists |
| Module files | Lines 135-138 | `cli.py`, `store.py` exist |
| Entry point | Lines 141-143 | `__main__.py` exists |
| Add command works | Lines 151-159 | `python -m todo add "Test task"` returns 0 |
| List command works | Lines 161-173 | `python -m todo list` shows added task |

### Current PhaseRunner Prompts

#### Discovery Prompt (Lines 453-464)

```python
discovery_prompt = (
    f"Perform Discovery and Planning for the following Sprint Goal:\n"
    f"'{goal}'\n\n"
    f"INSTRUCTIONS:\n"
    f"1. Analyze the requirements carefully.\n"
    f"2. Create 'implementation_plan.md' using `fs_write_file` with:\n"
    f"   - A list of ALL files to be created (with full paths)\n"
    f"   - Package/module structure if applicable\n"
    f"   - Step-by-step implementation order\n"
    f"   - Key functions/classes for each file\n"
    f"3. Use `fs_write_file` to create the implementation_plan.md file.\n"
    f"4. Return 'Discovery Complete' when done."
)
```

**Issues:**
- No explicit instruction to preserve exact file paths from goal
- "Package/module structure if applicable" is ambiguous
- No validation that planned files match goal requirements

#### Coding Prompt (Lines 592-604)

```python
coding_prompt = (
    f"Phase 2: Coding (Attempt {attempt + 1})\n"
    f"SPRINT GOAL: {goal[:500]}{'...' if len(goal) > 500 else ''}\n\n"
    f"CRITICAL INSTRUCTIONS:\n"
    f"1. Read 'implementation_plan.md' using `fs_read_file` to see the file list.\n"
    f"2. Create ALL files listed in the plan using `fs_write_file`.\n"
    f"3. For multi-file projects:\n"
    f"   - Create package directories (e.g., 'todo/__init__.py')\n"
    f"   - Create each module file with complete implementation\n"
    f"   - Include `__main__.py` if the plan calls for it\n"
    f"4. Use `fs_list_dir` to verify all files were created.\n"
    f"5. Return 'Coding Complete' ONLY after ALL planned files exist."
)
```

**Issues:**
- Relies on `implementation_plan.md` which may not match goal exactly
- No reminder of specific files required from the original goal
- No instruction to verify package is runnable with `python -m`

#### Verification Prompt (Lines 700-711)

```python
base_verification_prompt = (
    f"Phase 3: Verification (Attempt {attempt + 1})\n"
    f"SPRINT GOAL: {goal[:300]}{'...' if len(goal) > 300 else ''}\n\n"
    f"VERIFICATION STEPS:\n"
    f"1. Use `fs_list_dir` to see all created files.\n"
    f"2. Read 'implementation_plan.md' to check file list against created files.\n"
    f"3. For CLI tools: Create a test script that exercises the main functionality.\n"
    f"4. For packages: Verify the package can be imported and run.\n"
    f"5. Use `run_tests()` to execute any test files in the workspace.\n"
    f"6. CRITICAL: Return 'VERIFICATION_SUCCESS' only if the code works correctly.\n"
    f"7. Return 'VERIFICATION_FAILURE' with details if anything fails."
)
```

**Issues:**
- "Create a test script" is vague - doesn't specify what to test
- No explicit instruction to run `python -m <package>` for CLI packages
- Goal is truncated to 300 chars, losing important detail

---

### Gap Analysis

| Test Expectation | Current Prompt Instruction | Gap |
|------------------|---------------------------|-----|
| `todo/__init__.py` | "Package directories if applicable" | IMPLICIT - not enforced |
| `cli.py`, `store.py` | "Create ALL files listed in plan" | INDIRECT - depends on plan quality |
| `__main__.py` | "Include if the plan calls for it" | CONDITIONAL - not mandated |
| `python -m todo add` | "exercises main functionality" | VAGUE - no specific command |
| JSON storage at `~/.todo_test.json` | Not mentioned | MISSING |
| argparse, no external deps | Not mentioned in prompts | MISSING |

---

## Recommendations

### Option A: Enhanced Goal-Specific Prompts (RECOMMENDED)

**Pros:**
- Maintains flexibility for different sprint types
- Adds explicit structure validation
- Backward compatible

**Cons:**
- Requires goal parsing logic
- Slightly more complex prompts

**Implementation:**

1. **Discovery Prompt Enhancement:**

```python
discovery_prompt = (
    f"Perform Discovery and Planning for the following Sprint Goal:\n"
    f"'{goal}'\n\n"
    f"CRITICAL REQUIREMENTS FROM GOAL (preserve exactly):\n"
    f"- Extract ALL file paths mentioned (e.g., 'todo/__init__.py')\n"
    f"- Extract ALL commands/functions mentioned\n"
    f"- Extract ALL constraints (no external deps, storage locations)\n\n"
    f"INSTRUCTIONS:\n"
    f"1. Analyze the requirements carefully.\n"
    f"2. Create 'implementation_plan.md' using `fs_write_file` with:\n"
    f"   - EXACT file list from goal (do NOT rename or reorganize)\n"
    f"   - Step-by-step implementation order\n"
    f"   - Key functions/classes for each file\n"
    f"3. Use `fs_write_file` to create the implementation_plan.md file.\n"
    f"4. Return 'Discovery Complete' when done."
)
```

2. **Coding Prompt Enhancement:**

```python
coding_prompt = (
    f"Phase 2: Coding (Attempt {attempt + 1})\n"
    f"SPRINT GOAL (reference this for exact requirements):\n"
    f"'{goal}'\n\n"  # Full goal, not truncated
    f"CRITICAL INSTRUCTIONS:\n"
    f"1. Read 'implementation_plan.md' using `fs_read_file` to see the file list.\n"
    f"2. Create ALL files listed in the plan using `fs_write_file`.\n"
    f"3. For multi-file projects:\n"
    f"   - Create package directories (e.g., 'todo/__init__.py')\n"
    f"   - Create each module file with COMPLETE, WORKING implementation\n"
    f"   - ALWAYS create `__main__.py` for CLI packages\n"
    f"4. VERIFY: Use `fs_list_dir` to confirm all files exist.\n"
    f"5. VERIFY: For CLI tools, the command `python -m <package>` MUST work.\n"
    f"6. Return 'Coding Complete' ONLY after ALL files exist and are complete."
)
```

3. **Verification Prompt Enhancement:**

```python
base_verification_prompt = (
    f"Phase 3: Verification (Attempt {attempt + 1})\n"
    f"SPRINT GOAL:\n"
    f"'{goal}'\n\n"  # Full goal, not truncated
    f"VERIFICATION CHECKLIST:\n"
    f"1. [ ] Use `fs_list_dir` to see all created files.\n"
    f"2. [ ] Verify EVERY file from goal exists:\n"
    f"       - Read implementation_plan.md\n"
    f"       - Confirm each planned file was created\n"
    f"3. [ ] For CLI packages:\n"
    f"       - Run `python -m <package> --help` or similar\n"
    f"       - Test EACH command mentioned in goal\n"
    f"4. [ ] For libraries: Import and call key functions\n"
    f"5. [ ] Check for import errors or syntax issues\n\n"
    f"Return 'VERIFICATION_SUCCESS' only if ALL checks pass.\n"
    f"Return 'VERIFICATION_FAILURE' with SPECIFIC failure details."
)
```

**Feasibility:** HIGH
**Effort:** S (Small) - 2-4 hours
**Risk:** LOW - Changes are additive

---

### Option B: Goal-Aware Prompt Templates

**Pros:**
- Highly specific prompts per project type
- Maximum control over output

**Cons:**
- Requires goal classification system
- More complex maintenance

**Implementation:**

Create template prompts for different project types:

```python
PROMPT_TEMPLATES = {
    "cli_package": {
        "discovery": "...",
        "coding": "...",
        "verification": "..."
    },
    "library": {...},
    "script": {...}
}

def detect_project_type(goal: str) -> str:
    if "CLI" in goal or "python -m" in goal:
        return "cli_package"
    elif "import" in goal or "library" in goal:
        return "library"
    return "script"
```

**Feasibility:** MEDIUM
**Effort:** M (Medium) - 1-2 days
**Risk:** MEDIUM - New abstraction layer

---

### Option C: Custom Evaluator for Package Structure

Add a deterministic evaluator that validates package structure:

```python
class PackageStructureEvaluator:
    """Validates expected files exist based on goal parsing."""

    async def evaluate(self, phase, output, context):
        goal = context.get("goal", "")
        workspace = context.get("workspace_ref")

        # Extract expected files from goal
        expected_files = self._parse_expected_files(goal)

        # Check each exists
        missing = []
        for f in expected_files:
            if not (Path(workspace) / f).exists():
                missing.append(f)

        if missing:
            return EvaluationResult(
                passed=False,
                feedback=f"Missing files: {missing}",
                suggestions=[f"Create {f}" for f in missing]
            )
        return EvaluationResult(passed=True, score=1.0)
```

**Feasibility:** HIGH
**Effort:** S (Small) - 2-4 hours
**Risk:** LOW - Complements existing evaluators

---

## Recommended Approach: Combined A + C

1. **Implement Option A** - Enhanced prompts (immediate impact)
2. **Implement Option C** - Package structure evaluator (validation safety net)

This provides:
- Better instructions (prompts guide AI correctly)
- Validation safety net (evaluator catches failures)
- Minimal code changes
- Backward compatibility

---

## Best Practices for Deterministic AI Output

Based on research, these prompt engineering techniques improve consistency:

### 1. Explicit Checklists
```
CHECKLIST (complete ALL items):
[ ] File todo/__init__.py created
[ ] File todo/cli.py created
[ ] ...
```

### 2. Negative Constraints
```
DO NOT:
- Rename files from the goal
- Use external dependencies
- Create additional files not in the goal
```

### 3. Verification Steps
```
BEFORE returning success:
1. List all files with fs_list_dir
2. Run the main command to verify it works
3. Check output matches expected behavior
```

### 4. Anchoring to Source Material
```
REFERENCE: The goal specifies EXACTLY these files:
- todo/__init__.py
- todo/cli.py
- todo/store.py
- todo/__main__.py

Create ONLY these files with EXACTLY these names.
```

### 5. Success Criteria
```
SUCCESS = ALL of the following:
- All 4 files exist
- `python -m todo add "Test"` returns exit code 0
- `python -m todo list` shows "Test" in output
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Prompt changes break other sprints | LOW | MEDIUM | Add tests for other sprint types |
| AI ignores enhanced instructions | MEDIUM | LOW | Evaluator catches failures |
| Goal parsing fails for edge cases | LOW | LOW | Fallback to current behavior |

---

## Next Steps

1. **Phase 1 (Day 1):** Implement enhanced prompts (Option A)
2. **Phase 2 (Day 1):** Add PackageStructureEvaluator (Option C)
3. **Phase 3 (Day 2):** Run integration tests, iterate on prompts
4. **Phase 4 (Day 2):** Document prompt patterns for future sprints

---

## Recommended Skills

Based on this research, the following installed skills are relevant:

| Skill | Category | Why Relevant |
|-------|----------|--------------|
| `dspy` | prompt-engineering | Declarative prompt optimization |
| `guidance` | prompt-engineering | Constrained generation patterns |
| `outlines` | prompt-engineering | Structured output from LLMs |

**How to use:**
```bash
cat skills/ai-research-prompt-engineering-dspy/SKILL.md
cat skills/ai-research-prompt-engineering-guidance/SKILL.md
cat skills/ai-research-prompt-engineering-outlines/SKILL.md
```

---

## References

- `backend/tests/integration/test_agent_browser_todolist.py` - Test expectations
- `backend/app/runners/phase_runner.py` - Current prompt implementation
- `backend/app/runners/evaluators/` - Evaluator pattern
- `docs/sprints.md` - Sprint workflow documentation
- `docs/design/evaluator-optimizer-architecture.md` - Evaluator-optimizer pattern

---

## Appendix: Proposed Prompt Diffs

### Discovery Prompt Diff

```diff
 discovery_prompt = (
     f"Perform Discovery and Planning for the following Sprint Goal:\n"
     f"'{goal}'\n\n"
+    f"CRITICAL: Extract and preserve EXACT requirements from the goal:\n"
+    f"- File names/paths (create these EXACTLY as specified)\n"
+    f"- Commands/functions (implement ALL mentioned)\n"
+    f"- Constraints (no external deps, storage locations, etc.)\n\n"
     f"INSTRUCTIONS:\n"
     f"1. Analyze the requirements carefully.\n"
     f"2. Create 'implementation_plan.md' using `fs_write_file` with:\n"
-    f"   - A list of ALL files to be created (with full paths)\n"
-    f"   - Package/module structure if applicable\n"
+    f"   - EXACT file list from goal (do NOT rename or reorganize)\n"
+    f"   - Package structure EXACTLY as specified in goal\n"
     f"   - Step-by-step implementation order\n"
     f"   - Key functions/classes for each file\n"
     f"3. Use `fs_write_file` to create the implementation_plan.md file.\n"
     f"4. Return 'Discovery Complete' when done."
 )
```

### Coding Prompt Diff

```diff
 coding_prompt = (
     f"Phase 2: Coding (Attempt {attempt + 1})\n"
-    f"SPRINT GOAL: {goal[:500]}{'...' if len(goal) > 500 else ''}\n\n"
+    f"SPRINT GOAL:\n{goal}\n\n"
     f"CRITICAL INSTRUCTIONS:\n"
     f"1. Read 'implementation_plan.md' using `fs_read_file` to see the file list.\n"
     f"2. Create ALL files listed in the plan using `fs_write_file`.\n"
     f"3. For multi-file projects:\n"
     f"   - Create package directories (e.g., 'todo/__init__.py')\n"
-    f"   - Create each module file with complete implementation\n"
-    f"   - Include `__main__.py` if the plan calls for it\n"
+    f"   - Create each module file with COMPLETE, WORKING code\n"
+    f"   - ALWAYS include `__main__.py` for CLI packages\n"
     f"4. Use `fs_list_dir` to verify all files were created.\n"
-    f"5. Return 'Coding Complete' ONLY after ALL planned files exist."
+    f"5. For CLI tools: Verify `python -m <package>` would work.\n"
+    f"6. Return 'Coding Complete' ONLY after ALL files exist AND are complete."
 )
```

### Verification Prompt Diff

```diff
 base_verification_prompt = (
     f"Phase 3: Verification (Attempt {attempt + 1})\n"
-    f"SPRINT GOAL: {goal[:300]}{'...' if len(goal) > 300 else ''}\n\n"
+    f"SPRINT GOAL:\n{goal}\n\n"
-    f"VERIFICATION STEPS:\n"
+    f"VERIFICATION CHECKLIST (complete ALL):\n"
     f"1. Use `fs_list_dir` to see all created files.\n"
-    f"2. Read 'implementation_plan.md' to check file list against created files.\n"
-    f"3. For CLI tools: Create a test script that exercises the main functionality.\n"
-    f"4. For packages: Verify the package can be imported and run.\n"
+    f"2. Verify EACH file from the goal exists:\n"
+    f"   - Compare against implementation_plan.md\n"
+    f"   - All specified files MUST exist\n"
+    f"3. For CLI tools:\n"
+    f"   - Run `python -m <package> --help` or equivalent\n"
+    f"   - Test EACH command specified in goal\n"
+    f"   - Verify output matches expected behavior\n"
+    f"4. For packages: Import and run key functions.\n"
     f"5. Use `run_tests()` to execute any test files in the workspace.\n"
-    f"6. CRITICAL: Return 'VERIFICATION_SUCCESS' only if the code works correctly.\n"
-    f"7. Return 'VERIFICATION_FAILURE' with details if anything fails."
+    f"6. Return 'VERIFICATION_SUCCESS' only if ALL checks pass.\n"
+    f"7. Return 'VERIFICATION_FAILURE' with SPECIFIC failure reason."
 )
```

---

*Report generated: 2026-01-22*
*Author: Research Scientist Agent*
