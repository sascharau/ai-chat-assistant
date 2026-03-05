"""File read/write tools with path traversal protection."""
from pathlib import Path
from typing import Any

from core.tools import register_tools
from core.tools.base import Tool, RiskLevel


class ReadFileTool(Tool):
    def __init__(self, working_dir: Path):
        self._working_dir = working_dir

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the content of a file."

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to the file"},
            },
            "required": ["path"],
        }

    async def execute(self, input_data: dict[str, Any], *, chat_id: str) -> str:
        rel_path = input_data["path"]
        file_path = (self._working_dir / rel_path).resolve()

        # Path Traversal verhindern
        if not str(file_path).startswith(str(self._working_dir.resolve())):
            return "Error: access outside working directory not allowed."

        if not file_path.exists():
            return f"Error: file '{rel_path}' not found."

        if not file_path.is_file():
            return f"Error: '{rel_path}' is not a file."

        content = file_path.read_text(encoding="utf-8")
        if len(content) > 100_000:
            return content[:100_000] + "\n\n[... truncated, file too large]"
        return content


class WriteFileTool(Tool):
    def __init__(self, working_dir: Path):
        self._working_dir = working_dir

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file. Creates parent directories if needed."

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to the file"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        }

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.MEDIUM

    async def execute(self, input_data: dict[str, Any], *, chat_id: str) -> str:
        rel_path = input_data["path"]
        file_path = (self._working_dir / rel_path).resolve()

        if not str(file_path).startswith(str(self._working_dir.resolve())):
            return "Error: access outside working directory not allowed."

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(input_data["content"], encoding="utf-8")
        return f"File '{rel_path}' written ({len(input_data['content'])} chars)."


register_tools("read_file", lambda config: ReadFileTool(config.data_dir / "working_dir"))
register_tools("write_file", lambda config: WriteFileTool(config.data_dir / "working_dir"))
