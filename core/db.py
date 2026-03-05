import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Message:
    chat_id: str
    sender: str
    content: str
    is_from_bot: bool = False
    timestamp: str | None = None


class Database:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")

    def run_migrations(self, migrations_dir: Path):
        """Execute SQL files in order."""
        # Migration tracking table
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY, applied_at TEXT)"
        )

        for sql_file in sorted(migrations_dir.glob("*.sql")):
            name = sql_file.name
            already_applied = self.conn.execute(
                "SELECT 1 FROM _migrations WHERE name = ?", (name,)
            ).fetchone()

            if not already_applied:
                sql = sql_file.read_text()
                self.conn.executescript(sql)
                self.conn.execute(
                    "INSERT INTO _migrations (name, applied_at) VALUES (?, ?)",
                    (name, datetime.now(timezone.utc).isoformat()),
                )
                self.conn.commit()

    def ensure_chat(self, chat_id: str, channel: str, name: str = "", is_group: bool = False):
        """Create chat if it doesn't exist."""
        self.conn.execute(
            """INSERT OR IGNORE INTO chats (chat_id, chat_name, channel, is_group)
               VALUES (?, ?, ?, ?)""",
            (chat_id, name, channel, int(is_group)),
        )
        self.conn.commit()

    def save_message(self, msg: Message):
        """Save a message."""
        self.conn.execute(
            """INSERT INTO messages (chat_id, sender, content, is_from_bot, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (msg.chat_id, msg.sender, msg.content, int(msg.is_from_bot),
             msg.timestamp or datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def get_history(self, chat_id: str, limit: int = 50) -> list[Message]:
        """Return the last N messages for a chat."""
        rows = self.conn.execute(
            """SELECT chat_id, sender, content, is_from_bot, timestamp
               FROM messages WHERE chat_id = ?
               ORDER BY id DESC LIMIT ?""",
            (chat_id, limit),
        ).fetchall()
        return [
            Message(
                chat_id=r["chat_id"], sender=r["sender"], content=r["content"],
                is_from_bot=bool(r["is_from_bot"]), timestamp=r["timestamp"],
            )
            for r in reversed(rows)
        ]

    # --- Sessions ---

    def load_session(self, chat_id: str) -> list[dict] | None:
        """Load a saved LLM session."""
        row = self.conn.execute(
            "SELECT messages_json FROM sessions WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        if row:
            return json.loads(row["messages_json"])
        return None

    def save_session(self, chat_id: str, messages: list[dict]):
        """Save an LLM session (JSON blob)."""
        self.conn.execute(
            """INSERT INTO sessions (chat_id, messages_json, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(chat_id) DO UPDATE SET
                 messages_json = excluded.messages_json,
                 updated_at = excluded.updated_at""",
            (chat_id, json.dumps(messages, ensure_ascii=False),
             datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    # --- Scheduled Tasks ---

    def get_due_tasks(self) -> list[dict]:
        """Return tasks whose next_run is in the past."""
        now = datetime.now(timezone.utc).isoformat()
        rows = self.conn.execute(
            """SELECT * FROM scheduled_tasks
               WHERE status = 'active' AND next_run <= ?""",
            (now,),
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()