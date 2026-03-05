"""
Main process: Assemble everything and start.

Procedure:
1. Load configuration
2. Initialize database + migrations
3. Connect channels (auto-discovery)
4. Register tools
5. Wire message handler
6. Start scheduler
7. Run continuously
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path

import structlog

from core.agent.engine import process_message
from core.channels import create_channels, IncomingMessage
from core.config import load_config
from core.db import Database
from core.scheduler import start_scheduler
from core.tools import create_tools

logger = structlog.get_logger()


async def run():
    # 1. load config
    config = load_config()
    logger.info("Configuration loaded", assistant=config.assistant_name)

    # 2. Initialize database
    db = Database(config.resolve_db_path())
    migrations_dir = Path(__file__).parent.parent / "migrations"
    if migrations_dir.exists():
        db.run_migrations(migrations_dir)
    logger.info("Database ready", path=str(config.resolve_db_path()))

    # 3. Create channels
    channels = create_channels(config)
    if not channels:
        logger.error("No channels configured! At least one channel is required.")
        logger.error("Set TELEGRAM_BOT_TOKEN in the .env file, for example.")
        sys.exit(1)
    logger.info("Registered channels", channels=[c.name for c in channels])

    # 4. Register tools
    tools = create_tools(config)
    logger.info("Tools registered", count=len(tools), names=[t.name for t in tools])

    # 5. Message handler
    async def handle_message(msg: IncomingMessage):
        """Process an incoming message."""
        # Create chat in DB (if new)
        db.ensure_chat(msg.chat_id, msg.channel, is_group=msg.is_group)

        # Save message
        db.save_message(
            __import__("aiboy.db", fromlist=["Message"]).Message(
                chat_id=msg.chat_id,
                sender=msg.sender_name,
                content=msg.content,
                is_from_bot=False,
                timestamp=msg.timestamp.isoformat(),
            )
        )

        # Trigger check: in groups only respond to @mention
        trigger = f"@{config.assistant_name.lower()}"
        if msg.is_group and not msg.content.lower().startswith(trigger):
            return

        logger.info(
            "Message received",
            chat_id=msg.chat_id,
            sender=msg.sender_name,
            channel=msg.channel,
        )

        # Run agent
        try:
            reply = await process_message(msg.chat_id, msg.content, db, config, tools)
        except Exception:
            logger.exception("Agent error")
            reply = "Sorry, an error occurred."

        # Send reply
        channel = next((ch for ch in channels if ch.owns_chat_id(msg.chat_id)), None)
        if channel:
            await channel.send_message(msg.chat_id, reply)

        # Save reply to DB
        db.save_message(
            __import__("aiboy.db", fromlist=["Message"]).Message(
                chat_id=msg.chat_id,
                sender=config.assistant_name,
                content=reply,
                is_from_bot=True,
            )
        )

    # 6. Connect channels
    for channel in channels:
        await channel.connect(handle_message)
        logger.info("Channel connected", channel=channel.name)

    # 7. Start scheduler (in background)
    async def process_task(task: dict) -> str:
        reply = await process_message(task["chat_id"], task["prompt"], db, config, tools)
        # Send result to chat
        channel = next((ch for ch in channels if ch.owns_chat_id(task["chat_id"])), None)
        if channel:
            await channel.send_message(task["chat_id"], reply)
        return reply

    scheduler_task = asyncio.create_task(start_scheduler(db, process_task))

    logger.info(
        f"{config.assistant_name} running",
        channels=[ch.name for ch in channels],
        tools=[t.name for t in tools],
    )

    # 8. Wait for shutdown
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await stop_event.wait()

    # Cleanup
    logger.info("Shutting down...")
    scheduler_task.cancel()
    for channel in channels:
        await channel.shutdown()
    db.close()


def main():
    """CLI Entry Point."""
    logging.basicConfig(level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
    )
    asyncio.run(run())


if __name__ == "__main__":
    main()