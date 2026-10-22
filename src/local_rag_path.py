"""
Shared import-path setup for the sibling local-rag project.

Both the interactive CLI and eval runner import src.nodes, so the local-rag
path must be registered from src rather than from a single entrypoint.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def ensure_local_rag_path() -> Path:
    """Add the sibling local-rag project to sys.path and return its path."""
    local_rag_path = Path(
        os.environ.get(
            "LOCAL_RAG_PATH",
            Path(__file__).resolve().parents[2] / "local-rag",
        )
    ).resolve()

    path_str = str(local_rag_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

    return local_rag_path
