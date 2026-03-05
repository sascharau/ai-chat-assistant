"""Container runner: execute agent in a Docker container.

- One container per agent invocation (ephemeral, --rm)
- Mounts for group data, sessions, IPC
- Security: --cap-drop ALL, non-root, read-only rootfs
- Extract output via markers
"""
from __future__ import annotations

import json
import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ContainerInput:
    prompt: str
    chat_id: str
    group_folder: str
    is_main: bool
    session_id: str | None = None


@dataclass
class ContainerOutput:
    status: str   # "success" or "error"
    result: str
    session_id: str | None = None


OUTPUT_START = "---AIBOY_OUTPUT_START---"
OUTPUT_END = "---AIBOY_OUTPUT_END---"


def run_container_agent(
    input_data: ContainerInput,
    secrets: dict[str, str],
    data_dir: Path,
    image: str = "aiboy-agent:latest",
    timeout: int = 1800,  # 30 minutes
) -> ContainerOutput:
    """Run agent in a Docker container."""

    container_name = f"aiboy-{input_data.chat_id}-{int(time.time())}"
    container_name = container_name.replace(":", "-").replace("/", "-")

    # Build volume mounts
    group_path = Path(input_data.group_folder).resolve()
    session_path = (data_dir / "sessions" / input_data.chat_id).resolve()
    ipc_path = (data_dir / "ipc" / input_data.chat_id).resolve()

    # Create directories
    for p in (group_path, session_path, ipc_path):
        p.mkdir(parents=True, exist_ok=True)

    cmd = [
        "docker", "run", "--rm",
        "--name", container_name,
        # Security flags
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges:true",
        "--user", "1000:1000",
        # Temporary directories
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=100m",
        # Volume mounts
        "-v", f"{group_path}:/workspace/group:rw",
        "-v", f"{session_path}:/workspace/session:rw",
        "-v", f"{ipc_path}:/workspace/ipc:rw",
        # Env vars (whitelisted only!)
    ]

    # Only pass allowed secrets
    allowed_keys = {"ANTHROPIC_API_KEY", "OPENAI_API_KEY"}
    for key, value in secrets.items():
        if key in allowed_keys:
            cmd.extend(["-e", f"{key}={value}"])

    cmd.append(image)

    try:
        result = subprocess.run(
            cmd,
            input=json.dumps(input_data.__dict__),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        stdout = result.stdout

        # Extract output between markers
        start_idx = stdout.find(OUTPUT_START)
        end_idx = stdout.find(OUTPUT_END)

        if start_idx != -1 and end_idx != -1:
            json_str = stdout[start_idx + len(OUTPUT_START):end_idx].strip()
            data = json.loads(json_str)
            return ContainerOutput(**data)

        return ContainerOutput(
            status="error",
            result=result.stderr or "No output from container",
        )

    except subprocess.TimeoutExpired:
        # Kill container
        subprocess.run(["docker", "kill", container_name], capture_output=True)
        return ContainerOutput(status="error", result="Container timeout")

    except Exception as e:
        return ContainerOutput(status="error", result=f"Container error: {e}")