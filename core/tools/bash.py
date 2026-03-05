"""Shell-Execution Tool."""
import asyncio
import subprocess
from typing import Any

from core.tools import register_tools
from core.tools.base import Tool, RiskLevel


class BashTool(Tool):
    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return "Execute a shell command and return stdout/stderr."

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
            },
            "required": ["command"],
        }

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.HIGH

    async def execute(self, input_data: dict[str, Any], *, chat_id: str) -> str:
        command = input_data["command"]

        # Execute in a separate thread (does not block the event loop)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/tmp",  # Security: not in the project directory
            ),
        )

        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        if result.returncode != 0:
            output += f"\nExit-Code: {result.returncode}"

        # Limit output (save LLM context).
        return output[:50_000]


register_tools("bash", lambda config: BashTool())
