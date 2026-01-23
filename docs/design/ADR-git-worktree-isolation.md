# ADR-010: Git Worktree Isolation for Sprints

## Status

**Proposed** - 2026-01-22

## Context

### Problem Statement

Agent-generated code is currently written to a shared artifacts directory (`AUTOCODE_ARTIFACTS_DIR`) without git isolation. This architecture presents several risks:

1. **Code Escape Risk**: If agent-generated code escapes the sandbox, it could affect the main repository or other sprints
2. **No Rollback Capability**: Without version control, reverting failed sprint changes requires manual intervention
3. **Branch Contamination**: The main branch could be polluted if sprints directly write to tracked directories
4. **Parallel Execution Conflicts**: Multiple concurrent sprints could overwrite each other's work
5. **No Change Audit Trail**: Without git history, understanding what the agent modified is difficult

### Current Architecture

The current system stores sprint artifacts in a flat directory structure:

```
AUTOCODE_ARTIFACTS_DIR/
└── {sprint_id}/
    ├── manifest.json
    ├── timeline.json
    ├── spec/
    ├── code/
    ├── phases/
    ├── candidates/
    └── checkpoints/
```

Key integration points:
- `WorkflowTracker.base_dir` points to `AUTOCODE_ARTIFACTS_DIR/{sprint_id}`
- `Deps.session_dir` is used by filesystem tools to scope file operations
- `PhaseRunner.start()` initializes the workflow tracker and creates directories

### Decision Drivers

1. **Safety**: Isolate agent changes from the main codebase until explicitly merged
2. **Auditability**: Full git history of agent modifications per sprint
3. **Rollback**: Easy reversal of failed sprint changes via branch deletion
4. **Parallelism**: Enable concurrent sprint executions without conflicts
5. **Integration**: Minimal changes to existing PhaseRunner and agent workflows
6. **Cleanup**: Automated removal of stale worktrees and branches

## Decision

Implement a `WorktreeManager` service that creates isolated git worktrees for each sprint execution. Each sprint operates in its own worktree on a dedicated branch, leaving the main branch untouched.

### Architecture Overview

```
WorktreeManager Service
├── create_worktree(sprint_id, base_branch="main") -> Path
│   └── Creates: worktrees/sprint-{uuid}/ on branch sprint/{uuid}
├── cleanup_worktree(sprint_id, delete_branch=False)
│   └── Removes worktree and optionally deletes branch
├── get_worktree_path(sprint_id) -> Path | None
├── list_active_worktrees() -> list[WorktreeInfo]
├── cleanup_stale_worktrees(max_age_hours=24)
└── merge_to_main(sprint_id, strategy="squash") -> MergeResult
```

### Directory Structure

```
{repository_root}/
├── .git/
│   └── worktrees/
│       ├── sprint-{uuid-1}/
│       └── sprint-{uuid-2}/
├── worktrees/                    # NEW: Worktree checkouts
│   ├── sprint-{uuid-1}/          # Full checkout for sprint 1
│   │   ├── backend/
│   │   ├── frontend/
│   │   └── ...
│   └── sprint-{uuid-2}/          # Full checkout for sprint 2
│       ├── backend/
│       ├── frontend/
│       └── ...
├── artifacts/                    # Existing artifact storage (metadata only)
│   ├── {sprint-uuid-1}/
│   │   ├── manifest.json
│   │   ├── timeline.json
│   │   └── phases/
│   └── {sprint-uuid-2}/
│       └── ...
└── (normal repo files)
```

### Integration Points

```
PhaseRunner.start()
├── Create worktree via WorktreeManager
├── Update Sprint model with worktree_ref and worktree_branch
├── Initialize WorkflowTracker with worktree path
└── Set Deps.session_dir to worktree path

PhaseRunner.cleanup()
├── Complete sprint (success/failure)
├── Optionally merge to main (on success)
└── Cleanup worktree via WorktreeManager

Deps
├── session_dir -> Points to worktree path
└── All filesystem tools scoped to worktree

Sprint Model (DB)
├── worktree_ref: str | None     # e.g., "worktrees/sprint-{uuid}"
├── worktree_branch: str | None  # e.g., "sprint/{uuid}"
└── worktree_status: WorktreeStatus  # created|merged|deleted
```

### Database Schema Changes

Add to `Sprint` model:

```python
class WorktreeStatus(StrEnum):
    """Worktree lifecycle status."""
    NONE = "none"           # No worktree (legacy sprints)
    CREATED = "created"     # Worktree exists
    MERGED = "merged"       # Changes merged to main
    DELETED = "deleted"     # Worktree removed

class Sprint(Base, TimestampMixin):
    # ... existing fields ...

    # Worktree isolation
    worktree_ref: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Relative path to worktree directory"
    )
    worktree_branch: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Git branch name for this sprint"
    )
    worktree_status: Mapped[WorktreeStatus] = mapped_column(
        Enum(WorktreeStatus, name="worktree_status"),
        default=WorktreeStatus.NONE,
        nullable=False,
    )
```

### WorktreeManager Implementation

```python
# backend/app/services/worktree.py

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID
import subprocess
import shutil
from datetime import datetime, timedelta

@dataclass
class WorktreeInfo:
    """Information about an active worktree."""
    sprint_id: UUID
    path: Path
    branch: str
    created_at: datetime
    commit_sha: str

class WorktreeError(Exception):
    """Base exception for worktree operations."""
    pass

class WorktreeManager:
    """Manages git worktrees for sprint isolation."""

    WORKTREE_DIR = "worktrees"
    BRANCH_PREFIX = "sprint"

    def __init__(self, repo_root: Path | None = None):
        """Initialize the worktree manager.

        Args:
            repo_root: Root of the git repository. Defaults to current repo.
        """
        self.repo_root = repo_root or self._find_repo_root()
        self.worktrees_dir = self.repo_root / self.WORKTREE_DIR

    def _find_repo_root(self) -> Path:
        """Find the root of the current git repository."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())

    def _run_git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command in the repository root."""
        return subprocess.run(
            ["git", *args],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=check,
        )

    def _validate_repo_state(self) -> None:
        """Validate repository is in a clean state for worktree creation."""
        result = self._run_git("status", "--porcelain", check=False)
        # We allow dirty state - worktrees are independent
        # But we need to verify we're in a valid git repo
        if result.returncode != 0:
            raise WorktreeError(f"Not a valid git repository: {result.stderr}")

    async def create_worktree(
        self,
        sprint_id: UUID,
        base_branch: str = "main",
    ) -> Path:
        """Create an isolated worktree for a sprint.

        Args:
            sprint_id: The sprint UUID
            base_branch: Branch to base the worktree on

        Returns:
            Path to the created worktree

        Raises:
            WorktreeError: If worktree creation fails
        """
        self._validate_repo_state()

        # Ensure worktrees directory exists
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)

        worktree_name = f"sprint-{sprint_id}"
        worktree_path = self.worktrees_dir / worktree_name
        branch_name = f"{self.BRANCH_PREFIX}/{sprint_id}"

        # Check if worktree already exists
        if worktree_path.exists():
            raise WorktreeError(f"Worktree already exists: {worktree_path}")

        # Fetch latest from remote to ensure we have the base branch
        self._run_git("fetch", "origin", base_branch, check=False)

        # Create new branch and worktree in one command
        # -b creates a new branch, worktree path, branch name
        try:
            self._run_git(
                "worktree", "add",
                "-b", branch_name,
                str(worktree_path),
                f"origin/{base_branch}",
            )
        except subprocess.CalledProcessError as e:
            # Try with local base branch if remote doesn't exist
            try:
                self._run_git(
                    "worktree", "add",
                    "-b", branch_name,
                    str(worktree_path),
                    base_branch,
                )
            except subprocess.CalledProcessError as e2:
                raise WorktreeError(
                    f"Failed to create worktree: {e2.stderr}"
                ) from e2

        return worktree_path

    async def cleanup_worktree(
        self,
        sprint_id: UUID,
        delete_branch: bool = False,
    ) -> None:
        """Remove a sprint worktree.

        Args:
            sprint_id: The sprint UUID
            delete_branch: Whether to also delete the branch

        Raises:
            WorktreeError: If cleanup fails
        """
        worktree_name = f"sprint-{sprint_id}"
        worktree_path = self.worktrees_dir / worktree_name
        branch_name = f"{self.BRANCH_PREFIX}/{sprint_id}"

        # Remove worktree (git command)
        if worktree_path.exists():
            try:
                self._run_git("worktree", "remove", str(worktree_path), "--force")
            except subprocess.CalledProcessError:
                # Manual cleanup if git fails
                shutil.rmtree(worktree_path, ignore_errors=True)

        # Prune worktree metadata
        self._run_git("worktree", "prune", check=False)

        # Optionally delete the branch
        if delete_branch:
            self._run_git("branch", "-D", branch_name, check=False)

    async def get_worktree_path(self, sprint_id: UUID) -> Path | None:
        """Get the path to a sprint's worktree if it exists.

        Args:
            sprint_id: The sprint UUID

        Returns:
            Path to worktree or None if not found
        """
        worktree_name = f"sprint-{sprint_id}"
        worktree_path = self.worktrees_dir / worktree_name

        if worktree_path.exists() and worktree_path.is_dir():
            return worktree_path
        return None

    async def list_active_worktrees(self) -> list[WorktreeInfo]:
        """List all active sprint worktrees.

        Returns:
            List of WorktreeInfo for each active worktree
        """
        result = self._run_git("worktree", "list", "--porcelain", check=False)
        if result.returncode != 0:
            return []

        worktrees = []
        current_worktree: dict = {}

        for line in result.stdout.strip().split("\n"):
            if not line:
                if current_worktree.get("path", "").startswith(str(self.worktrees_dir)):
                    # Extract sprint ID from path
                    path = Path(current_worktree["path"])
                    if path.name.startswith("sprint-"):
                        try:
                            sprint_id = UUID(path.name.replace("sprint-", ""))
                            worktrees.append(WorktreeInfo(
                                sprint_id=sprint_id,
                                path=path,
                                branch=current_worktree.get("branch", "").replace("refs/heads/", ""),
                                created_at=datetime.now(),  # Would need stat for accurate time
                                commit_sha=current_worktree.get("HEAD", ""),
                            ))
                        except ValueError:
                            pass  # Invalid UUID, skip
                current_worktree = {}
            elif line.startswith("worktree "):
                current_worktree["path"] = line.replace("worktree ", "")
            elif line.startswith("HEAD "):
                current_worktree["HEAD"] = line.replace("HEAD ", "")
            elif line.startswith("branch "):
                current_worktree["branch"] = line.replace("branch ", "")

        return worktrees

    async def cleanup_stale_worktrees(
        self,
        max_age_hours: int = 24,
    ) -> list[UUID]:
        """Remove worktrees older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours before cleanup

        Returns:
            List of sprint IDs that were cleaned up
        """
        cleaned = []
        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        if not self.worktrees_dir.exists():
            return cleaned

        for path in self.worktrees_dir.iterdir():
            if not path.is_dir() or not path.name.startswith("sprint-"):
                continue

            # Check directory modification time
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            if mtime < cutoff:
                try:
                    sprint_id = UUID(path.name.replace("sprint-", ""))
                    await self.cleanup_worktree(sprint_id, delete_branch=False)
                    cleaned.append(sprint_id)
                except (ValueError, WorktreeError):
                    pass

        return cleaned

    async def commit_changes(
        self,
        sprint_id: UUID,
        message: str,
        author: str = "Sprint Agent <agent@guilde.ai>",
    ) -> str:
        """Commit all changes in a worktree.

        Args:
            sprint_id: The sprint UUID
            message: Commit message
            author: Git author string

        Returns:
            Commit SHA
        """
        worktree_path = await self.get_worktree_path(sprint_id)
        if not worktree_path:
            raise WorktreeError(f"Worktree not found for sprint {sprint_id}")

        # Stage all changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=worktree_path,
            check=True,
        )

        # Commit with author
        result = subprocess.run(
            ["git", "commit", "-m", message, f"--author={author}"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False,
        )

        # Get commit SHA
        sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
        )

        return sha_result.stdout.strip()

    async def merge_to_main(
        self,
        sprint_id: UUID,
        strategy: str = "squash",
        main_branch: str = "main",
    ) -> dict:
        """Merge sprint branch to main.

        Args:
            sprint_id: The sprint UUID
            strategy: Merge strategy (merge, squash, rebase)
            main_branch: Target branch name

        Returns:
            Dict with merge result info
        """
        branch_name = f"{self.BRANCH_PREFIX}/{sprint_id}"

        # Checkout main
        self._run_git("checkout", main_branch)

        # Pull latest
        self._run_git("pull", "origin", main_branch, check=False)

        # Merge based on strategy
        if strategy == "squash":
            self._run_git("merge", "--squash", branch_name)
            self._run_git(
                "commit", "-m",
                f"feat(sprint): Merge sprint {sprint_id}\n\nSquashed commits from {branch_name}"
            )
        elif strategy == "rebase":
            self._run_git("rebase", branch_name)
        else:
            self._run_git("merge", branch_name)

        # Get merge commit
        result = self._run_git("rev-parse", "HEAD")

        return {
            "strategy": strategy,
            "branch": branch_name,
            "target": main_branch,
            "commit": result.stdout.strip(),
        }
```

### Configuration Changes

Add to `Settings` class:

```python
# backend/app/core/config.py

class Settings(BaseSettings):
    # ... existing settings ...

    # === Git Worktree Settings ===
    GIT_WORKTREE_ENABLED: bool = True
    GIT_WORKTREE_BASE_BRANCH: str = "main"
    GIT_WORKTREE_CLEANUP_ON_COMPLETION: bool = True
    GIT_WORKTREE_DELETE_BRANCH_ON_CLEANUP: bool = False
    GIT_WORKTREE_MAX_AGE_HOURS: int = 24
    GIT_WORKTREE_AUTO_COMMIT: bool = True
    GIT_WORKTREE_DIR: str = "worktrees"  # Relative to repo root
```

### PhaseRunner Integration

```python
# Updated PhaseRunner.start()

@classmethod
async def start(cls, sprint_id: UUID) -> None:
    """Start the phase runner for a sprint as a background task."""
    await asyncio.sleep(1)
    logger.info(f"Starting PhaseRunner for sprint {sprint_id}")

    room = str(sprint_id)
    worktree_path: Path | None = None
    worktree_manager: WorktreeManager | None = None

    # ... existing broadcast helpers ...

    async with get_db_context() as db:
        sprint_service = SprintService(db)
        agent_tdd_service = AgentTddService(db)
        spec_service = SpecService(db)

        try:
            sprint = await sprint_service.get_by_id(sprint_id)
            goal = sprint.goal or sprint.name

            # === NEW: Create isolated worktree ===
            if settings.GIT_WORKTREE_ENABLED:
                worktree_manager = WorktreeManager()
                worktree_path = await worktree_manager.create_worktree(
                    sprint_id=sprint_id,
                    base_branch=settings.GIT_WORKTREE_BASE_BRANCH,
                )

                # Update sprint with worktree info
                await sprint_service.update(
                    sprint_id,
                    SprintUpdate(
                        worktree_ref=str(worktree_path.relative_to(worktree_manager.repo_root)),
                        worktree_branch=f"sprint/{sprint_id}",
                        worktree_status=WorktreeStatus.CREATED,
                    )
                )

                logger.info(f"Created worktree at {worktree_path}")

            # Initialize workflow tracker
            tracker = WorkflowTracker(
                sprint_id=sprint_id,
                spec_id=sprint.spec_id,
                artifacts_dir=settings.AUTOCODE_ARTIFACTS_DIR,
                worktree_path=worktree_path,  # NEW: Pass worktree path
            )
            await tracker.start_sprint()

            # ... rest of phase execution ...

        except Exception as e:
            logger.error(f"PhaseRunner failed for sprint {sprint_id}: {e}")
            # ... error handling ...

        finally:
            # === NEW: Cleanup worktree on completion ===
            if worktree_manager and settings.GIT_WORKTREE_CLEANUP_ON_COMPLETION:
                try:
                    # Commit any uncommitted changes first
                    if settings.GIT_WORKTREE_AUTO_COMMIT:
                        await worktree_manager.commit_changes(
                            sprint_id,
                            f"feat(sprint): Final state of sprint {sprint_id}"
                        )

                    # Cleanup (but keep branch for review)
                    await worktree_manager.cleanup_worktree(
                        sprint_id,
                        delete_branch=settings.GIT_WORKTREE_DELETE_BRANCH_ON_CLEANUP,
                    )

                    # Update sprint status
                    await sprint_service.update(
                        sprint_id,
                        SprintUpdate(worktree_status=WorktreeStatus.DELETED)
                    )
                except Exception as cleanup_error:
                    logger.warning(f"Worktree cleanup failed: {cleanup_error}")
```

### Updated Deps Integration

```python
# backend/app/agents/deps.py

@dataclass
class Deps:
    """Dependencies for the assistant agent."""

    user_id: str | None = None
    user_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    session_dir: Path | None = None  # Points to worktree when isolation enabled
    worktree_path: Path | None = None  # Explicit worktree reference
    worktree_branch: str | None = None  # Branch name for commits

    @property
    def working_dir(self) -> Path | None:
        """Get the effective working directory for file operations."""
        return self.worktree_path or self.session_dir
```

## Consequences

### Positive

1. **Complete Isolation**: Agent changes never touch main branch until explicitly merged
2. **Full Audit Trail**: Git history shows exactly what the agent modified
3. **Easy Rollback**: Simply delete the branch to discard all sprint changes
4. **Parallel Safety**: Multiple sprints can execute concurrently without conflicts
5. **Merge Control**: Human review before merging agent changes to main
6. **Existing Tool Compatibility**: Git-based tools (diff, log, blame) work naturally
7. **Incremental Commits**: Agent can commit at each phase for granular history

### Negative

1. **Disk Space**: Full repository checkout per sprint (~500MB-2GB depending on repo size)
2. **Complexity**: Additional git operations and error handling
3. **Network**: May need to fetch from remote for base branch
4. **Cleanup Overhead**: Stale worktrees need periodic cleanup
5. **Lock Contention**: Git index lock if too many concurrent operations

### Mitigations

| Risk | Mitigation |
|------|------------|
| Disk space | Auto-cleanup after 24 hours; sparse checkout option for large repos |
| Complexity | Comprehensive error handling; fallback to non-isolated mode |
| Network | Cache base branch; allow local-only mode |
| Cleanup | Background cleanup job; startup cleanup |
| Lock contention | Per-worktree operations; retry with backoff |

### Migration Path

1. **Phase 1**: Feature flag (`GIT_WORKTREE_ENABLED=false` by default)
2. **Phase 2**: Enable for new sprints, existing sprints use legacy path
3. **Phase 3**: Migrate artifact storage to worktrees
4. **Phase 4**: Remove legacy artifact directory support

## Alternatives Considered

### 1. Docker Volume Isolation

**Description**: Create isolated Docker volumes for each sprint with a fresh git clone.

**Pros**:
- Complete filesystem isolation
- No worktree complexity

**Cons**:
- Requires Docker
- Slower (full clone per sprint)
- More resource intensive
- No branch-based workflow

**Decision**: Rejected. Git worktrees are lighter weight and provide better integration with git-based workflows.

### 2. Directory-Based Isolation (Current)

**Description**: Keep current approach with separate directories per sprint.

**Pros**:
- Simple implementation
- Already working

**Cons**:
- No git isolation
- No rollback capability
- No audit trail
- Potential for code escape

**Decision**: Rejected. Does not meet safety and auditability requirements.

### 3. Git Submodules

**Description**: Use git submodules for sprint code.

**Pros**:
- Well-established pattern
- Clear separation

**Cons**:
- Complex submodule management
- Not designed for ephemeral branches
- Adds permanent structure to repo

**Decision**: Rejected. Submodules are designed for long-lived dependencies, not ephemeral sprint work.

### 4. Shallow Clone Per Sprint

**Description**: Create a shallow git clone for each sprint.

**Pros**:
- Complete isolation
- Smaller disk footprint than full clone

**Cons**:
- Slower than worktree (network required)
- No shared git history
- Cannot easily merge back

**Decision**: Rejected. Worktrees provide better performance and git integration.

## Implementation Plan

### Phase 1: Core Implementation (This ADR)

1. Create `WorktreeManager` service
2. Add database migration for Sprint worktree fields
3. Add configuration settings
4. Unit tests for WorktreeManager

**Files**:
- `backend/app/services/worktree.py` (new)
- `backend/app/db/models/sprint.py` (update)
- `backend/app/core/config.py` (update)
- `backend/tests/unit/test_worktree_manager.py` (new)
- `backend/alembic/versions/YYYY-MM-DD_add_worktree_fields.py` (new)

### Phase 2: PhaseRunner Integration

1. Integrate WorktreeManager with PhaseRunner
2. Update Deps to use worktree path
3. Update WorkflowTracker to write to worktree
4. Integration tests

**Files**:
- `backend/app/runners/phase_runner.py` (update)
- `backend/app/agents/deps.py` (update)
- `backend/app/services/workflow_tracker.py` (update)
- `backend/tests/integration/test_worktree_isolation.py` (new)

### Phase 3: Cleanup and Monitoring

1. Startup cleanup for stale worktrees
2. Background cleanup job
3. Monitoring/metrics for worktree operations
4. Admin API endpoints for worktree management

**Files**:
- `backend/app/main.py` (update - startup hook)
- `backend/app/api/routes/v1/admin.py` (new/update)
- `backend/app/tasks/cleanup.py` (new)

### Phase 4: Merge Workflow

1. API endpoint to trigger merge
2. PR creation option for human review
3. Conflict resolution guidance
4. Branch protection integration

**Files**:
- `backend/app/api/routes/v1/sprints.py` (update)
- `backend/app/services/sprint.py` (update)

## File Structure

```
backend/app/
├── services/
│   ├── worktree.py              # NEW: WorktreeManager service
│   ├── sprint.py                # UPDATE: Add worktree operations
│   └── workflow_tracker.py      # UPDATE: Use worktree path
├── db/
│   └── models/
│       └── sprint.py            # UPDATE: Add worktree fields
├── runners/
│   └── phase_runner.py          # UPDATE: Create/cleanup worktree
├── agents/
│   └── deps.py                  # UPDATE: Add worktree properties
├── core/
│   └── config.py                # UPDATE: Add worktree settings
├── api/routes/v1/
│   └── sprints.py               # UPDATE: Add merge endpoint
└── tasks/
    └── cleanup.py               # NEW: Cleanup background job

backend/tests/
├── unit/
│   └── test_worktree_manager.py # NEW: Unit tests
└── integration/
    └── test_worktree_isolation.py # NEW: Integration tests

backend/alembic/versions/
└── 2026-01-22_add_worktree_fields.py  # NEW: Migration
```

## Related Skills

The following installed skills provide implementation guidance:

- `using-git-worktrees` - For git worktree CLI patterns and best practices
- `pytest-testing` - For comprehensive test coverage of worktree operations

Read with: `cat skills/<skill-name>/SKILL.md`

---

## Appendix A: Git Worktree Commands Reference

```bash
# Create worktree with new branch
git worktree add -b sprint/uuid worktrees/sprint-uuid origin/main

# List worktrees
git worktree list --porcelain

# Remove worktree
git worktree remove worktrees/sprint-uuid --force

# Prune stale worktree metadata
git worktree prune

# Lock worktree (prevent removal)
git worktree lock worktrees/sprint-uuid

# Move worktree
git worktree move worktrees/sprint-uuid /new/path
```

---

## Appendix B: Example Workflow

```
Sprint Creation:
1. API receives POST /sprints with spec_id
2. Sprint created in DB with status=PLANNED
3. PhaseRunner.start() triggered

Worktree Setup:
1. WorktreeManager.create_worktree(sprint_id, "main")
2. Creates: worktrees/sprint-{uuid}/
3. Creates branch: sprint/{uuid} from main
4. Sprint updated: worktree_ref, worktree_branch, worktree_status=CREATED

Phase Execution:
1. Deps.session_dir = worktrees/sprint-{uuid}/
2. Agent writes files to worktree
3. Agent commits at phase boundaries (optional)
4. WorkflowTracker records metadata to artifacts/

Sprint Completion:
1. Final commit with all changes
2. Sprint status = COMPLETED
3. Worktree cleaned up (directory removed)
4. Branch preserved for review/merge

Merge (optional):
1. Human reviews sprint/{uuid} branch
2. API receives POST /sprints/{id}/merge
3. WorktreeManager.merge_to_main(sprint_id, "squash")
4. Sprint worktree_status = MERGED
5. Branch optionally deleted
```

---

## Appendix C: Error Handling Matrix

| Error | Cause | Recovery |
|-------|-------|----------|
| `WorktreeError: already exists` | Stale worktree from crashed sprint | Cleanup and retry |
| `Git lock timeout` | Concurrent git operation | Retry with exponential backoff |
| `Branch already exists` | Previous sprint with same ID | Use unique branch suffix |
| `Merge conflict` | Agent changes conflict with main | Create PR for human resolution |
| `Disk full` | Too many worktrees | Trigger emergency cleanup |
| `Git not found` | Missing git binary | Fail with clear error message |
