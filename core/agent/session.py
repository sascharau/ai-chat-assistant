from datetime import datetime, timezone
from pathlib import Path

import anthropic

from core.config import Config

MAX_SESSION_MESSAGES = 40
COMPACT_KEEP_RECENT = 10


async def compact_session(
    messages: list[dict],
    client: anthropic.Anthropic,
    config: Config,
) -> list[dict]:
    """Summarize older messages when the session gets too long.

    The LLM summarizes old messages while recent messages are preserved.
    """
    if len(messages) <= MAX_SESSION_MESSAGES:
        return messages

    old_messages = messages[:-COMPACT_KEEP_RECENT]
    recent_messages = messages[-COMPACT_KEEP_RECENT:]

    # Only user/assistant text messages for summary
    summary_text = _format_messages_for_summary(old_messages)
    if not summary_text.strip():
        return recent_messages

    response = client.messages.create(
        model=config.llm.model,
        max_tokens=1024,
        system=(
            "Summarize the following conversation in 2-3 paragraphs. "
            "Retain important facts, decisions, and context information."
        ),
        messages=[{"role": "user", "content": summary_text}],
    )

    summary = response.content[0].text

    return [
        {"role": "user", "content": f"[Summary of previous conversation]\n{summary}"},
        {"role": "assistant", "content": "Understood, I have the context."},
        *recent_messages,
    ]


def _format_messages_for_summary(messages: list[dict]) -> str:
    """Convert messages to readable format for the summary prompt."""
    lines = []
    for msg in messages:
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if isinstance(content, str):
            lines.append(f"{role}: {content}")
        elif isinstance(content, list):
            # Simplify tool_use / tool_result blocks
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    lines.append(f"{role}: {block['text']}")
    return "\n".join(lines)


def build_system_prompt(chat_id: str, config: Config) -> str:
    """Build the system prompt.

    Uses SOUL.md (global identity) + per-group MEMORY.md for context.
    """
    parts: list[str] = []

    # 1. Base identity (SOUL.md)
    soul_path = config.data_dir / "SOUL.md"
    if soul_path.exists():
        parts.append(soul_path.read_text(encoding="utf-8"))
    else:
        parts.append(
            f"You are {config.assistant_name}, a helpful personal assistant. "
            f"You respond precisely and in a friendly manner."
        )

    # 2. Per-group memory
    group_memory_path = config.data_dir / "groups" / _sanitize_folder(chat_id) / "MEMORY.md"
    if group_memory_path.exists():
        memory = group_memory_path.read_text(encoding="utf-8")
        parts.append(f"\n## Context for this chat\n{memory}")

    # 3. Current time
    now = datetime.now(timezone.utc).isoformat()
    parts.append(f"\nCurrent time: {now}\nTimezone: {config.timezone}")

    return "\n\n".join(filter(None, parts))


def _sanitize_folder(chat_id: str) -> str:
    """Convert chat ID to a safe folder name."""
    return chat_id.replace(":", "_").replace("/", "_").replace("..", "")