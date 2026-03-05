"""Per-group memory: each chat has its own MEMORY.md.

- Simple file-based persistence
- Vector search can be added later
"""
from __future__ import annotations

from pathlib import Path


class MemoryManager:
    def __init__(self, data_dir: Path):
        self._groups_dir = data_dir / "groups"
        self._groups_dir.mkdir(parents=True, exist_ok=True)

    def _group_path(self, chat_id: str) -> Path:
        folder = chat_id.replace(":", "_").replace("/", "_").replace("..", "")
        return self._groups_dir / folder

    def _memory_file(self, chat_id: str) -> Path:
        return self._group_path(chat_id) / "MEMORY.md"

    def read(self, chat_id: str) -> str:
        """Read memory for a chat."""
        path = self._memory_file(chat_id)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def write(self, chat_id: str, content: str) -> None:
        """Write memory for a chat."""
        path = self._memory_file(chat_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def append(self, chat_id: str, entry: str) -> None:
        """Append an entry to memory."""
        current = self.read(chat_id)
        new_content = f"{current}\n\n{entry}".strip()
        self.write(chat_id, new_content)

    def read_global(self) -> str:
        """Read global memory (SOUL.md)."""
        path = self._groups_dir.parent / "SOUL.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""