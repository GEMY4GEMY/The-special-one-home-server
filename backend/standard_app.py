"""Offline Standard edition: no AI endpoints or AI engine required."""
import json
import secrets
import sqlite3
from pydantic import BaseModel, Field
from backend.app import password_hash
from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from backend.app import FRONTEND
from backend.app import app, admin_only, db, init_question_tables

# Disable inference routes in this edition, even if a client calls them directly.
app.router.routes[:] = [
    route for route in app.router.routes
    if not getattr(route, "path", "").startswith("/api/admin/ai/")
    and getattr(route, "path", "") != "/api/admin/pdf-vision"
    and getattr(route, "path", "") not in ("/api/exams", "/api/exams/{exam_id}", "/api/exams/{exam_id}/submit")
]

@app.post("/api/admin/question-bank/import")
async def import_question_bank(file: UploadFile = File(...), user=Depends(admin_only)):
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
    with db() as conn:
        init_question_tables(conn)
        conn.executemany(
            "INSERT INTO question_bank (grade,unit,lesson,difficulty,kind,prompt,answer,options) VALUES (?,?,?,?,?,?,?,?)",
            rows,
        )
    return {"imported": len(rows), "status": "complete"}


class PublicStudentSignup(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=128)
    grade: str = Field(min_length=2, max_length=80)

@app.post("/api/standard/register", status_code=201)
def register_student(payload: PublicStudentSignup):
    """Public registration can create student accounts only, never admins."""
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
