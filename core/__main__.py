"""
Main process: Assemble everything and start.

Procedure:
1. Load configuration
2. Initialize database + migrations
3. Register tools
4. Connect channels (auto-discovery)
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


logger = structlog.get_logger()


async def run():
    # 1. load config
    config = load_config()
    logger.info("Konfiguration geladen", assistant=config.assistant_name)

    # 2. Initialize database
    db = Database(config.resolve_db_path())
    migrations_dir = Path(__file__).parent.parent / "migrations"
    if migrations_dir.exists():
        db.run_migrations(migrations_dir)
    logger.info("Database ready", path=str(config.resolve_db_path()))

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