# AI Chat Assistant
The project's goal is to gain an understanding of how OpenCLaw works and to draw conclusions from it.

## Architecture

**Monolith approach** — the entire application runs in a single process:
The bot starts, connects to configured channels (e.g. Telegram), and processes messages through the agent engine — all within a single process. No container-per-request isolation. (next)
