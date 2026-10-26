"""Offline Standard edition: no AI endpoints or AI engine required."""
import json
import secrets
import sqlite3
from pydantic import BaseModel, Field
from backend.app import password_hash
from fastapi import Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from backend.app import FRONTEND
from backend.app import app, admin_only, db, init_question_tables, ADMIN_USERNAME, password_hash as hasher, sessions
from fastapi import Response
import hashlib

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
    with db() as conn:
        init_question_tables(conn)
        conn.executemany(
            "INSERT INTO question_bank (grade,unit,lesson,difficulty,kind,prompt,answer,options) VALUES (?,?,?,?,?,?,?,?)",
            rows,
        )
    return {"imported": len(rows), "grade": grade or "From JSON", "status": "complete"}


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
