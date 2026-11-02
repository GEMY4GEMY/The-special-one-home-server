"""Offline Standard edition: no AI endpoints or AI engine required."""
import json
import secrets
import sqlite3
from pydantic import BaseModel, Field
from backend.app import password_hash
from fastapi import Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response as DownloadResponse
from backend.app import FRONTEND
from backend.app import app, admin_only, db, init_question_tables, ADMIN_USERNAME, password_hash as hasher, sessions
from fastapi import Response
import hashlib
import tempfile
from contextlib import closing
from pathlib import Path
from backend.app import DB_PATH
from datetime import datetime, timezone

# Disable inference routes in this edition, even if a client calls them directly.
app.router.routes[:] = [
    route for route in app.router.routes
    if not getattr(route, "path", "").startswith("/api/admin/ai/")
    and getattr(route, "path", "") != "/api/admin/pdf-vision"
    and getattr(route, "path", "") not in ("/api/exams", "/api/exams/{exam_id}", "/api/exams/{exam_id}/submit")
]

@app.post("/api/admin/question-bank/import")
async def import_question_bank(file: UploadFile = File(...), stage: str | None = Form(None), grade: str | None = Form(None), user=Depends(admin_only)):
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(400, "Upload a .json question bank")
    data = await file.read(3 * 1024 * 1024 + 1)
    if len(data) > 3 * 1024 * 1024:
        raise HTTPException(413, "Question bank exceeds 3 MB")
    try:
        from backend.standard_import import validate_bank
        rows = validate_bank(json.loads(data.decode("utf-8-sig")))
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise HTTPException(422, str(exc))
    if stage is not None or grade is not None:
        allowed = {"Primary": 6, "Preparatory": 3, "Secondary": 3}
        if stage not in allowed or grade not in [f"{stage} {i}" for i in range(1, allowed.get(stage, 0) + 1)]:
            raise HTTPException(422, "Select a valid stage and grade for import")
        # Assign all questions to the explicitly chosen class, regardless of file metadata.
        rows = [(grade, *row[1:]) for row in rows]
    batch_id = secrets.token_urlsafe(16)
    with db() as conn:
        init_import_batches(conn)
        conn.execute(
            "INSERT INTO standard_import_batches(id,filename,grade,question_count,imported_at) VALUES (?,?,?,?,?)",
            (batch_id, file.filename, grade or "From JSON", len(rows), datetime.now(timezone.utc).isoformat()),
        )
        conn.executemany(
            "INSERT INTO question_bank (grade,unit,lesson,difficulty,kind,prompt,answer,options,import_batch_id) VALUES (?,?,?,?,?,?,?,?,?)",
            [(*row, batch_id) for row in rows],
        )
    return {"imported": len(rows), "grade": grade or "From JSON", "batch_id": batch_id, "status": "complete"}


def init_import_batches(conn):
    init_question_tables(conn)
    conn.execute("CREATE TABLE IF NOT EXISTS standard_import_batches (id TEXT PRIMARY KEY, filename TEXT NOT NULL, grade TEXT NOT NULL, question_count INTEGER NOT NULL, imported_at TEXT NOT NULL)")
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(question_bank)")}
    if "import_batch_id" not in columns:
        conn.execute("ALTER TABLE question_bank ADD COLUMN import_batch_id TEXT")


@app.get("/api/admin/standard/import-batches")
def list_import_batches(user=Depends(admin_only)):
    with db() as conn:
        init_import_batches(conn)
        return [dict(row) for row in conn.execute(
            "SELECT b.id,b.filename,b.grade,b.imported_at,COUNT(q.id) AS question_count "
            "FROM standard_import_batches b LEFT JOIN question_bank q ON q.import_batch_id=b.id "
            "GROUP BY b.id ORDER BY b.imported_at DESC"
        )]



@app.delete("/api/admin/standard/import-batches/{batch_id}")
def delete_import_batch(batch_id: str, user=Depends(admin_only)):
    """Delete one imported file's questions, but never silently break existing exams."""
    with db() as conn:
        init_import_batches(conn)
        batch = conn.execute("SELECT id FROM standard_import_batches WHERE id=?", (batch_id,)).fetchone()
        if not batch:
            raise HTTPException(404, "Imported file not found")
        ids = {row["id"] for row in conn.execute("SELECT id FROM question_bank WHERE import_batch_id=?", (batch_id,))}
        if ids:
            for draft in conn.execute("SELECT question_ids FROM exam_drafts"):
                if ids.intersection(json.loads(draft["question_ids"])):
                    raise HTTPException(409, "This file contains questions used by an exam. Remove or replace the exam before deleting the file.")
        conn.execute("DELETE FROM question_bank WHERE import_batch_id=?", (batch_id,))
        conn.execute("DELETE FROM standard_import_batches WHERE id=?", (batch_id,))
    return {"deleted_questions": len(ids), "deleted_batch_id": batch_id}


@app.get("/api/admin/standard/backup")
def download_standard_backup(user=Depends(admin_only)):
    """Download a consistent SQLite snapshot, including accounts, exams and results."""
    with tempfile.TemporaryDirectory(prefix="tso-backup-") as directory:
        destination = Path(directory) / "the-special-one-backup.sqlite3"
        with closing(sqlite3.connect(str(DB_PATH))) as source:
            with closing(sqlite3.connect(str(destination))) as target:
                source.backup(target)
        content = destination.read_bytes()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return DownloadResponse(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="THE_SPECIAL_ONE_BACKUP_{stamp}.sqlite3"',
                 "Cache-Control": "no-store"},
    )


@app.post("/api/admin/standard/restore")
async def restore_standard_backup(file: UploadFile = File(...), user=Depends(admin_only)):
    """Restore a validated SQLite backup; invalidate login sessions afterward."""
    max_bytes = 50 * 1024 * 1024
    if not file.filename or not file.filename.lower().endswith((".sqlite3", ".db")):
        raise HTTPException(400, "Choose a .sqlite3 backup file")
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(413, "Backup exceeds 50 MB")
    if not content.startswith(b"SQLite format 3\x00"):
        raise HTTPException(422, "Not a SQLite database")
    with tempfile.TemporaryDirectory(prefix="tso-restore-") as directory:
        incoming = Path(directory) / "incoming.sqlite3"
        incoming.write_bytes(content)
        try:
            with closing(sqlite3.connect(f"file:{incoming}?mode=ro", uri=True)) as source:
                if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise HTTPException(422, "SQLite integrity check failed")
                tables = {row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                required = {"users", "students", "question_bank", "exam_drafts"}
                if not required.issubset(tables):
                    raise HTTPException(422, "Backup is missing required application tables")
                required_columns = {
                    "users": {"id", "username", "password_hash", "role"},
                    "students": {"id", "user_id", "student_code", "full_name", "grade"},
                    "question_bank": {"id", "grade", "unit", "lesson", "difficulty", "kind", "prompt", "answer", "options"},
                    "exam_drafts": {"id", "title", "grade", "question_ids"},
                }
                for table, expected in required_columns.items():
                    actual = {row[1] for row in source.execute(f"PRAGMA table_info({table})")}
                    if not expected.issubset(actual):
                        raise HTTPException(422, f"Backup has incompatible {table} schema")
                admins = source.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
                if admins < 1:
                    raise HTTPException(422, "Backup has no administrator account")
                bad_drafts = source.execute("SELECT COUNT(*) FROM exam_drafts WHERE question_ids IS NULL OR NOT json_valid(question_ids)").fetchone()[0]
                if bad_drafts:
                    raise HTTPException(422, "Backup contains invalid exam drafts")
                # Make a recoverable copy of the current database before replacement.
                stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                safety = DB_PATH.parent / f"pre_restore_{stamp}.sqlite3"
                DB_PATH.parent.mkdir(parents=True, exist_ok=True)
                with closing(sqlite3.connect(str(DB_PATH), timeout=30)) as live:
                    with closing(sqlite3.connect(str(safety))) as old:
                        live.backup(old)
                    source.backup(live)
        except sqlite3.DatabaseError as exc:
            raise HTTPException(422, f"Invalid backup database: {exc}")
    sessions.clear()
    return {"restored": True, "login_required": True, "safety_backup": safety.name}


class PublicStudentSignup(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=128)
    stage: str = Field(min_length=1, max_length=30)
    grade: str = Field(min_length=2, max_length=80)

@app.post("/api/standard/register", status_code=201)
def register_student(payload: PublicStudentSignup):
    """Public registration can create student accounts only, never admins."""
    allowed = {"Primary": 6, "Preparatory": 3, "Secondary": 3}
    if payload.stage not in allowed or payload.grade not in [f"{payload.stage} {i}" for i in range(1, allowed[payload.stage] + 1)]:
        raise HTTPException(422, "Select a valid stage and grade")
    code = "STU-" + secrets.token_hex(6).upper()
    try:
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO users(username,password_hash,role) VALUES (?,?,?)",
                (payload.username, password_hash.hash(payload.password), "student"),
            )
            conn.execute(
                "INSERT INTO students(user_id,student_code,full_name,grade) VALUES (?,?,?,?)",
                (cur.lastrowid, code, payload.full_name.strip(), payload.grade.strip()),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Username already exists; choose another")
    return {"username": payload.username, "student_code": code, "role": "student"}

class AdminPasswordLogin(BaseModel):
    password: str

@app.post("/api/standard/admin-login")
def admin_password_login(payload: AdminPasswordLogin, response: Response):
    """Admin entry needs a password only; no username field on the public page."""
    with db() as conn:
        row = conn.execute("SELECT id,password_hash FROM users WHERE username=? AND role='admin'", (ADMIN_USERNAME,)).fetchone()
    if not row or not hasher.verify(payload.password, row["password_hash"]):
        raise HTTPException(401, "Invalid administrator password")
    token = secrets.token_urlsafe(32)
    sessions[hashlib.sha256(token.encode()).hexdigest()] = row["id"]
    response.set_cookie("tso_session", token, httponly=True, samesite="strict", secure=False, max_age=28800)
    return {"username": ADMIN_USERNAME, "role": "admin"}

@app.get('/api/edition')
def standard_edition():
    return {'edition':'standard'}

@app.get('/standard-home')
def standard_home():
    return FileResponse(FRONTEND / 'standard.html')

# A separate public landing route for Standard. The original AI edition keeps '/'.
@app.get("/api/standard/status")
def standard_status():
    return {"edition": "standard", "offline": True, "question_import": True}

# Register Standard-only published examination endpoints.
import backend.standard_exams

@app.get("/api/standard/health")
def standard_health():
    return {"status":"ok","edition":"standard","port":200}

import backend.standard_builder

import backend.standard_practice

import backend.standard_admin_results

import backend.standard_reports
