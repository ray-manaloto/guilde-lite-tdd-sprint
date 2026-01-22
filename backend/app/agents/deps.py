from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Deps:
    """Dependencies for the assistant agent.

    These are passed to tools via RunContext.
    """

    user_id: str | None = None
    user_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    session_dir: Path | None = None
