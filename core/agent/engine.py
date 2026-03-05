"""
Agentic loop: the core of the assistant.

1. Load session
2. Build system prompt
3. Call LLM
4. If tool call: execute tool → result → back to 3
5. Extract text response
6. Save session
"""

import logging

import anthropic

from core.config import Config
from core.db import Database
from core.agent.session import compact_session, build_system_prompt
from core.tools.base import Tool

logger = logging.getLogger(__name__)


async def process_message(
    chat_id: str,
    user_message: str,
    db: Database,
    config: Config,
    tools: list[Tool],
) -> str:
    """Process a message using the agentic loop (tool calls)."""

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    # 1. Load session or use history as fallback
    messages = db.load_session(chat_id) or []

    # 2. Compact session if too long
    messages = await compact_session(messages, client, config)

    # 3. Build system prompt
    system_prompt = build_system_prompt(chat_id, config)

    # 4. Append user message
    messages.append({"role": "user", "content": user_message})

    # 5. Tool definitions
    tool_defs = [t.definition() for t in tools]

    # 6. Agentic loop
    max_iterations = config.llm.max_tool_iterations
    for i in range(max_iterations):
        logger.debug(f"Agent iteration {i + 1}/{max_iterations} for {chat_id}")

        # Call LLM
        response = client.messages.create(
            model=config.llm.model,
            max_tokens=config.llm.max_tokens,
            system=system_prompt,
            messages=messages,
            tools=tool_defs if tool_defs else anthropic.NOT_GIVEN,
        )

        # Process tool calls
        if response.stop_reason == "tool_use":
            # Append assistant response (with tool_use blocks)
            messages.append({"role": "assistant", "content": _serialize_content(response.content)})

            # Collect tool results
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool = _find_tool(tools, block.name)
                if tool is None:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Error: Unknown tool '{block.name}'",
                        "is_error": True,
                    })
                    continue

                try:
                    result = await tool.execute(block.input, chat_id=chat_id)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })
                except Exception as e:
                    logger.exception(f"Tool {block.name} failed")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Error: {e}",
                        "is_error": True,
                    })

            messages.append({"role": "user", "content": tool_results})
            continue  # Next iteration

        # End turn: extract text response
        if response.stop_reason == "end_turn":
            reply = _extract_text(response.content)
            messages.append({"role": "assistant", "content": _serialize_content(response.content)})

            # Save session
            db.save_session(chat_id, messages)

            return reply

    return "Maximum iterations reached. Please try again."


def _serialize_content(content: list) -> list[dict]:
    """Convert Anthropic content blocks to JSON-serializable dicts."""
    result = []
    for block in content:
        if block.type == "text":
            result.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            result.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
    return result


def _extract_text(content: list) -> str:
    """Join text blocks from the LLM response."""
    parts = []
    for block in content:
        if block.type == "text":
            parts.append(block.text)
    return "\n".join(parts)


def _find_tool(tools: list[Tool], name: str) -> Tool | None:
    """Find a tool by name."""
    for tool in tools:
        if tool.name == name:
            return tool
    return None