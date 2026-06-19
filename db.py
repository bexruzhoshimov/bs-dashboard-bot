import sqlite3
from datetime import date, timedelta

DB_PATH = "bot.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT,
            calendar_event_id TEXT,
            calendar_link TEXT,
            reminder_sent INTEGER NOT NULL DEFAULT 0,
            done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    try:
        conn.execute("ALTER TABLE tasks ADD COLUMN done INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            week_start TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS listener_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_task(title, task_date, task_time, calendar_event_id=None, calendar_link=None):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO tasks (title, date, time, calendar_event_id, calendar_link, created_at) "
        "VALUES (?, ?, ?, ?, ?, datetime('now'))",
        (title, task_date, task_time, calendar_event_id, calendar_link),
    )
    conn.commit()
    task_id = cur.lastrowid
    conn.close()
    return task_id


def mark_done(task_id):
    conn = get_conn()
    conn.execute("UPDATE tasks SET done = 1 WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def get_task(task_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return row


def get_due_reminders(window_minutes=30):
    now = date.today()
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE reminder_sent = 0 AND time IS NOT NULL AND date = ?",
        (now.isoformat(),),
    ).fetchall()
    conn.close()
    from datetime import datetime
    due = []
    nowdt = datetime.now()
    for row in rows:
        task_dt = datetime.strptime(f"{row['date']} {row['time']}", "%Y-%m-%d %H:%M")
        delta = (task_dt - nowdt).total_seconds() / 60
        if 0 <= delta <= window_minutes:
            due.append(row)
    return due


def mark_reminded(task_id):
    conn = get_conn()
    conn.execute("UPDATE tasks SET reminder_sent = 1 WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def current_week_start():
    today = date.today()
    return (today - timedelta(days=today.weekday())).isoformat()


def add_goal(text):
    conn = get_conn()
    conn.execute(
        "INSERT INTO goals (text, week_start, created_at) VALUES (?, ?, datetime('now'))",
        (text, current_week_start()),
    )
    conn.commit()
    conn.close()


def get_week_goals(week_start):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM goals WHERE week_start = ? ORDER BY id", (week_start,)
    ).fetchall()
    conn.close()
    return rows


def get_offset():
    conn = get_conn()
    row = conn.execute("SELECT value FROM listener_state WHERE key = 'offset'").fetchone()
    conn.close()
    return int(row["value"]) if row else 0


def set_offset(offset):
    conn = get_conn()
    conn.execute(
        "INSERT INTO listener_state (key, value) VALUES ('offset', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(offset),),
    )
    conn.commit()
    conn.close()
