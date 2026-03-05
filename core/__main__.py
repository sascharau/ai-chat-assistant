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
from pathlib import Path

import structlog

from core.config import load_config
from core.db import Database
from core.channels import create_channels

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

    # 3. Create channels (auto-discovery)
    channels = create_channels(config)
    if not channels:
        logger.error("No channels configured! At least one channel is required.")
        logger.error("Set TELEGRAM_BOT_TOKEN in the .env file, for example.")
        sys.exit(1)


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