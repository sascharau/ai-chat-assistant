CREATE TABLE IF NOT EXISTS chats (
    chat_id   TEXT PRIMARY KEY,
    chat_name TEXT NOT NULL DEFAULT '',
    channel   TEXT NOT NULL,
    is_group  INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     TEXT NOT NULL REFERENCES chats(chat_id),
    sender      TEXT NOT NULL,
    content     TEXT NOT NULL,
    is_from_bot INTEGER NOT NULL DEFAULT 0,
    timestamp   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    chat_id       TEXT PRIMARY KEY REFERENCES chats(chat_id),
    messages_json TEXT NOT NULL,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id         TEXT NOT NULL REFERENCES chats(chat_id),
    prompt          TEXT NOT NULL,
    schedule_type   TEXT NOT NULL,  -- 'cron' or 'once'
    schedule_value  TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    next_run        TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS task_run_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL REFERENCES scheduled_tasks(id),
    status      TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    result      TEXT,
    error       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
