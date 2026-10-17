"""Single-worker local AI queue with durable SQLite task history.

Completed outputs survive restarts. Unfinished tasks are marked interrupted;
automatic replay is intentionally disabled to avoid duplicate model requests.
"""
import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from uuid import uuid4

executor = ThreadPoolExecutor(max_workers=1)
guard = Lock()
DB = Path(os.environ.get("TSO_DB_PATH", str(Path(__file__).resolve().parent / "data" / "local.sqlite3")))
ready = False

def _connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB, timeout=15)

def initialize():
    global ready
    with guard:
        if ready:
            return
        with _connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS ai_tasks (id TEXT PRIMARY KEY, owner INTEGER NOT NULL, state TEXT NOT NULL, output TEXT)")
            db.execute("UPDATE ai_tasks SET state='interrupted' WHERE state IN ('waiting','working')")
        ready = True

def submit(owner, work, *args):
    initialize()
    with guard:
        with _connect() as db:
            active = db.execute("SELECT COUNT(*) FROM ai_tasks WHERE state IN ('waiting','working')").fetchone()[0]
            if active >= 5:
                raise ValueError("Processing queue is full")
            key = uuid4().hex
            db.execute("INSERT INTO ai_tasks VALUES (?,?,?,NULL)", (key, owner, "waiting"))
    def runner():
        with _connect() as db:
            db.execute("UPDATE ai_tasks SET state='working' WHERE id=?", (key,))
        try:
            result = work(*args)
            payload = json.dumps(result, ensure_ascii=False)
            with _connect() as db:
                db.execute("UPDATE ai_tasks SET state='complete', output=? WHERE id=?", (payload, key))
        except Exception:
            with _connect() as db:
                db.execute("UPDATE ai_tasks SET state='failed' WHERE id=?", (key,))
    executor.submit(runner)
    return key

def lookup(key, owner):
    initialize()
    with _connect() as db:
        row = db.execute("SELECT state, output FROM ai_tasks WHERE id=? AND owner=?", (key, owner)).fetchone()
    if row is None:
        return None
    return {"id": key, "state": row[0], "output": json.loads(row[1]) if row[1] else None}
