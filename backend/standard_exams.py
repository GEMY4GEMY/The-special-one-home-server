"""Published Standard exams: question bank only; grading on server."""
import json
import secrets
import sqlite3
from datetime import datetime, timezone
from fastapi import Depends, HTTPException
from pydantic import BaseModel
from backend.app import app, db, admin_only, current_user, init_question_tables

class Submission(BaseModel):
    attempt_id: str
    answers: dict[str, str]

def init(conn):
    init_question_tables(conn)
    conn.execute("CREATE TABLE IF NOT EXISTS standard_publications (id TEXT PRIMARY KEY, draft_id TEXT UNIQUE NOT NULL, published_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS standard_visibility (publication_id TEXT PRIMARY KEY, active INTEGER NOT NULL DEFAULT 0)")
    conn.execute("CREATE TABLE IF NOT EXISTS standard_attempts (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, publication_id TEXT NOT NULL, attempt_id TEXT NOT NULL, score INTEGER NOT NULL, maximum INTEGER NOT NULL, submitted_at TEXT NOT NULL, UNIQUE(student_id,attempt_id))")

def student(user):
    if user["role"] != "student":
        raise HTTPException(403, "Student account required")
    return user

def normalize(s):
    return " ".join(s.casefold().strip().split()).rstrip(".!?")

@app.post("/api/standard/publish/{draft_id}")
def publish(draft_id: str, user=Depends(admin_only)):
    with db() as conn:
        init(conn)
        draft = conn.execute("SELECT id,question_ids FROM exam_drafts WHERE id=?", (draft_id,)).fetchone()
        if draft is None:
            raise HTTPException(404, "Draft not found")
        ids = json.loads(draft["question_ids"])
        if not ids:
            raise HTTPException(422, "Empty draft")
        count = conn.execute("SELECT COUNT(*) FROM question_bank WHERE id IN (" + ",".join("?" for _ in ids) + ")", ids).fetchone()[0]
        if count != len(ids):
            raise HTTPException(409, "Draft references missing questions")
        prior = conn.execute("SELECT id FROM standard_publications WHERE draft_id=?", (draft_id,)).fetchone()
        if prior:
            return {"id": prior["id"], "published": True}
        publication_id = secrets.token_urlsafe(18)
        conn.execute("INSERT INTO standard_publications VALUES (?,?,?)", (publication_id,draft_id,datetime.now(timezone.utc).isoformat()))
    return {"id": publication_id, "published": True}

@app.get("/api/standard/exams")
def published_exams(user=Depends(current_user)):
    student(user)
    with db() as conn:
        init(conn)
        grade = conn.execute("SELECT grade FROM students WHERE user_id=?", (user["id"],)).fetchone()
        if not grade:
            raise HTTPException(403, "Student profile missing")
        rows = conn.execute("SELECT p.id,d.title,d.grade,d.question_ids FROM standard_publications p JOIN exam_drafts d ON d.id=p.draft_id JOIN standard_visibility v ON v.publication_id=p.id AND v.active=1 WHERE d.grade=? ORDER BY p.published_at DESC LIMIT 1", (grade["grade"],)).fetchall()
        return [{"id":r["id"],"title":r["title"],"question_count":len(json.loads(r["question_ids"]))} for r in rows]

def load_exam(conn, exam_id, user):
    row = conn.execute("SELECT d.title,d.grade,d.question_ids FROM standard_publications p JOIN exam_drafts d ON d.id=p.draft_id JOIN standard_visibility v ON v.publication_id=p.id AND v.active=1 WHERE p.id=?", (exam_id,)).fetchone()
    grade = conn.execute("SELECT grade FROM students WHERE user_id=?", (user["id"],)).fetchone()
    if not row or not grade or grade["grade"] != row["grade"]:
        raise HTTPException(404, "Exam not available")
    ids = json.loads(row["question_ids"])
    questions = conn.execute("SELECT * FROM question_bank WHERE id IN (" + ",".join("?" for _ in ids) + ")", ids).fetchall()
    by_id = {str(q["id"]):q for q in questions}
    if len(by_id) != len(ids):
        raise HTTPException(409, "Exam questions unavailable")
    return row, [by_id[str(i)] for i in ids]

@app.get("/api/standard/exams/{exam_id}")
def exam_detail(exam_id: str, user=Depends(current_user)):
    student(user)
    with db() as conn:
        init(conn)
        row, questions = load_exam(conn,exam_id,user)
        return {"id":exam_id,"title":row["title"],"questions":[{"id":str(q["id"]),"type":q["kind"],"prompt":q["prompt"],"options":json.loads(q["options"] or "[]")} for q in questions]}

@app.post("/api/standard/exams/{exam_id}/submit")
def submit(exam_id: str, payload: Submission, user=Depends(current_user)):
    student(user)
    if not 8 <= len(payload.attempt_id) <= 100:
        raise HTTPException(422, "Invalid attempt ID")
    with db() as conn:
        init(conn)
        row, questions = load_exam(conn,exam_id,user)
        allowed = {str(q["id"]) for q in questions}
        if not set(payload.answers).issubset(allowed) or any(not isinstance(v,str) or len(v)>500 for v in payload.answers.values()):
            raise HTTPException(422, "Invalid answers")
        previous = conn.execute("SELECT publication_id,score,maximum FROM standard_attempts WHERE student_id=? AND attempt_id=?", (user["id"],payload.attempt_id)).fetchone()
        if previous:
            if previous["publication_id"] != exam_id:
                raise HTTPException(409, "Attempt ID belongs to another exam")
            return {"score":previous["score"],"maximum":previous["maximum"],"already_submitted":True}
        score = sum(normalize(payload.answers.get(str(q["id"]),""))==normalize(q["answer"]) for q in questions)
        conn.execute("INSERT INTO standard_attempts(student_id,publication_id,attempt_id,score,maximum,submitted_at) VALUES (?,?,?,?,?,?)", (user["id"],exam_id,payload.attempt_id,score,len(questions),datetime.now(timezone.utc).isoformat()))
        return {"score":score,"maximum":len(questions),"already_submitted":False}

@app.get("/api/standard/my-attempts")
def standard_my_attempts(user=Depends(current_user)):
    student(user)
    with db() as conn:
        init(conn)
        return [dict(r) for r in conn.execute("SELECT publication_id,score,maximum,submitted_at FROM standard_attempts WHERE student_id=? ORDER BY id DESC", (user["id"],))]
