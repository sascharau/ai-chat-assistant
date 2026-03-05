"""Task scheduler: cron jobs and one-time tasks.

- Polling loop (every 60 seconds)
- Cron expressions via croniter
- Task status tracking in SQLite

"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Callable, Awaitable

from croniter import croniter

from core.db import Database

logger = logging.getLogger(__name__)

# Type for the task processing function
TaskProcessor = Callable[[dict], Awaitable[str]]


async def start_scheduler(db: Database, process_task: TaskProcessor):
    """Start the scheduler loop. Runs until the program exits."""
    logger.info("Scheduler started (interval: 60s)")

    while True:
        try:
            due_tasks = db.get_due_tasks()

            for task in due_tasks:
                logger.info(f"Task {task['id']} due: {task['prompt'][:50]}...")

                start_time = time.monotonic()
                try:
                    result = await process_task(task)
                    duration_ms = int((time.monotonic() - start_time) * 1000)

                    # Log success
                    _log_task_run(db, task["id"], "success", duration_ms, result=result)

                    # Calculate next run
                    _schedule_next_run(db, task)

                except Exception as e:
                    duration_ms = int((time.monotonic() - start_time) * 1000)
                    logger.exception(f"Task {task['id']} failed")
                    _log_task_run(db, task["id"], "error", duration_ms, error=str(e))

        except Exception:
            logger.exception("Scheduler error")

        await asyncio.sleep(60)


def _schedule_next_run(db: Database, task: dict):
    """Calculate the next execution time."""
    if task["schedule_type"] == "cron":
        cron = croniter(task["schedule_value"], datetime.now(timezone.utc))
        next_run = cron.get_next(datetime).isoformat()
        db.conn.execute(
            "UPDATE scheduled_tasks SET next_run = ? WHERE id = ?",
            (next_run, task["id"]),
        )
        db.conn.commit()
    elif task["schedule_type"] == "once":
        db.conn.execute(
            "UPDATE scheduled_tasks SET status = 'completed' WHERE id = ?",
            (task["id"],),
        )
        db.conn.commit()


def _log_task_run(
    db: Database,
    task_id: int,
    status: str,
    duration_ms: int,
    result: str | None = None,
    error: str | None = None,
):
    """Log a task run."""
    db.conn.execute(
        """INSERT INTO task_run_logs (task_id, status, duration_ms, result, error)
           VALUES (?, ?, ?, ?, ?)""",
        (task_id, status, duration_ms, result, error),
    )
    db.conn.commit()