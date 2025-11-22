# db.py
import sqlite3
from typing import List, Optional, Dict

DB_PATH = "data/tasks.db"

def _connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

def init_db():
    conn = _connect()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        deadline TEXT,
        priority TEXT,
        status TEXT DEFAULT 'active',
        category TEXT,
        reminder_at TEXT
    )""")
    conn.commit()
    conn.close()

def add_task(user_id: int, text: str, deadline: Optional[str]=None, priority: Optional[str]=None, category: Optional[str]=None, reminder_at: Optional[str]=None) -> int:
    conn = _connect()
    c = conn.cursor()
    c.execute("INSERT INTO tasks (user_id, text, deadline, priority, category, reminder_at) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, text, deadline, priority, category, reminder_at))
    task_id = c.lastrowid
    conn.commit()
    conn.close()
    return task_id

def get_tasks(user_id: int, status: Optional[str]=None) -> List[Dict]:
    conn = _connect()
    c = conn.cursor()
    if status:
        c.execute("SELECT id, text, deadline, priority, status, category, reminder_at FROM tasks WHERE user_id=? AND status=? ORDER BY id DESC", (user_id, status))
    else:
        c.execute("SELECT id, text, deadline, priority, status, category, reminder_at FROM tasks WHERE user_id=? ORDER BY id DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "text": r[1], "deadline": r[2], "priority": r[3], "status": r[4], "category": r[5], "reminder_at": r[6]} for r in rows]

def get_task(user_id: int, task_id: int) -> Optional[Dict]:
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT id, text, deadline, priority, status, category, reminder_at FROM tasks WHERE user_id=? AND id=?", (user_id, task_id))
    r = c.fetchone()
    conn.close()
    if r:
        return {"id": r[0], "text": r[1], "deadline": r[2], "priority": r[3], "status": r[4], "category": r[5], "reminder_at": r[6]}
    return None

def update_task(user_id: int, task_id: int, **kwargs):
    allowed = {"text","deadline","priority","status","category","reminder_at"}
    pairs = []
    vals = []
    for k,v in kwargs.items():
        if k in allowed:
            pairs.append(f"{k}=?")
            vals.append(v)
    if not pairs:
        return
    vals.extend([user_id, task_id])
    conn = _connect()
    c = conn.cursor()
    c.execute(f"UPDATE tasks SET {', '.join(pairs)} WHERE user_id=? AND id=?", tuple(vals))
    conn.commit()
    conn.close()

def delete_task(user_id: int, task_id: int):
    conn = _connect()
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE user_id=? AND id=?", (user_id, task_id))
    conn.commit()
    conn.close()

def tasks_with_upcoming_reminder(current_iso: str):
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT id, user_id, text, deadline, reminder_at FROM tasks WHERE reminder_at IS NOT NULL AND status='active' AND reminder_at<=?", (current_iso,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "user_id": r[1], "text": r[2], "deadline": r[3], "reminder_at": r[4]} for r in rows]
