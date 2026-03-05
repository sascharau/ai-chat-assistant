# AI Chat Assistant
The project's goal is to gain an understanding of how OpenCLaw works and to draw conclusions from it.

## Architecture

**Monolith approach** — the entire application runs in a single process:
The bot starts, connects to configured channels (e.g. Telegram), and processes messages through the agent engine — all within a single process. No container-per-request isolation.

## Setup

```bash
# Install dependencies
uv sync

# Configure
cp .env.example .env  # Add your API keys

# Run
uv run aiboy
```

## Configuration

Required environment variables:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Lint
uv run ruff check .
```
