"""Check whether the local Standard administrator must be created."""
import os
import sqlite3
from pathlib import Path

database = Path(os.environ["TSO_DB_PATH"])
database.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(database) as connection:
    table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone()
    admin = (
        connection.execute(
            "SELECT 1 FROM users WHERE username=? AND role='admin'",
            (os.environ.get("TSO_ADMIN_USERNAME", "Mrsameh"),),
        ).fetchone()
        if table else None
    )
print("NO" if admin else "YES")
