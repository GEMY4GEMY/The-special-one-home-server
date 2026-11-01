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
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(standard_publications)")}
    if "question_snapshot" not in columns:
        conn.execute("ALTER TABLE standard_publications ADD COLUMN question_snapshot TEXT")
    conn.execute("CREATE TABLE IF NOT EXISTS standard_visibility (publication_id TEXT PRIMARY KEY, active INTEGER NOT NULL DEFAULT 0)")
    conn.execute("CREATE TABLE IF NOT EXISTS standard_progress (student_id INTEGER NOT NULL, publication_id TEXT NOT NULL, attempt_id TEXT NOT NULL, answers TEXT NOT NULL, page INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL, PRIMARY KEY(student_id,publication_id))")
    conn.execute("CREATE TABLE IF NOT EXISTS standard_attempts (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, publication_id TEXT NOT NULL, attempt_id TEXT NOT NULL, score INTEGER NOT NULL, maximum INTEGER NOT NULL, submitted_at TEXT NOT NULL, UNIQUE(student_id,attempt_id))")

def snapshot_questions(conn, ids):
    if not ids:
        raise HTTPException(422, "Empty exam")
    marks = ",".join("?" for _ in ids)
    rows = conn.execute(f"SELECT * FROM question_bank WHERE id IN ({marks})", ids).fetchall()
    by_id = {str(row["id"]): dict(row) for row in rows}
    if len(by_id) != len(ids):
        raise HTTPException(409, "Exam references missing questions")
    return json.dumps([by_id[str(qid)] for qid in ids])


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
        conn.execute("INSERT INTO standard_publications(id,draft_id,published_at,question_snapshot) VALUES (?,?,?,?)", (publication_id,draft_id,datetime.now(timezone.utc).isoformat(),snapshot_questions(conn,ids)))
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

@app.get("/api/standard/resumable-exams")
def resumable_exams(user=Depends(current_user)):
    student(user)
    with db() as conn:
        init(conn)
        grade=conn.execute("SELECT grade FROM students WHERE user_id=?", (user["id"],)).fetchone()
        if not grade:
            return []
        rows=conn.execute(
            "SELECT p.id,d.title,sp.updated_at FROM standard_progress sp "
            "JOIN standard_publications p ON p.id=sp.publication_id "
            "JOIN exam_drafts d ON d.id=p.draft_id "
            "WHERE sp.student_id=? AND d.grade=? AND NOT EXISTS "
            "(SELECT 1 FROM standard_attempts a WHERE a.student_id=sp.student_id "
            "AND a.publication_id=sp.publication_id AND a.attempt_id=sp.attempt_id) "
            "ORDER BY sp.updated_at DESC", (user["id"],grade["grade"])
        ).fetchall()
        return [dict(row) for row in rows]


def load_exam(conn, exam_id, user):
    row = conn.execute("SELECT d.title,d.grade,d.question_ids,p.question_snapshot FROM standard_publications p JOIN exam_drafts d ON d.id=p.draft_id WHERE p.id=?", (exam_id,)).fetchone()
    grade = conn.execute("SELECT grade FROM students WHERE user_id=?", (user["id"],)).fetchone()
    if not row or not grade or grade["grade"] != row["grade"]:
        raise HTTPException(404, "Exam not available")
    if row["question_snapshot"]:
        return row, json.loads(row["question_snapshot"])
    ids = json.loads(row["question_ids"])
    questions = conn.execute("SELECT * FROM question_bank WHERE id IN (" + ",".join("?" for _ in ids) + ")", ids).fetchall()
    by_id = {str(q["id"]):dict(q) for q in questions}
    if len(by_id) != len(ids):
        raise HTTPException(409, "Exam questions unavailable")
    ordered = [by_id[str(i)] for i in ids]
    conn.execute("UPDATE standard_publications SET question_snapshot=? WHERE id=? AND question_snapshot IS NULL", (json.dumps(ordered), exam_id))
    return row, ordered

class ProgressPayload(BaseModel):
    attempt_id: str
    answers: dict[str, str]
    page: int = 0


@app.get("/api/standard/exams/{exam_id}/progress")
def get_progress(exam_id: str, user=Depends(current_user)):
    student(user)
    with db() as conn:
        init(conn)
        load_exam(conn, exam_id, user)
        row = conn.execute("SELECT attempt_id,answers,page FROM standard_progress WHERE student_id=? AND publication_id=?", (user["id"],exam_id)).fetchone()
        return {"attemptId":row["attempt_id"],"answers":json.loads(row["answers"]),"page":row["page"]} if row else None


@app.put("/api/standard/exams/{exam_id}/progress")
def save_progress(exam_id: str, payload: ProgressPayload, user=Depends(current_user)):
    student(user)
    if not 8 <= len(payload.attempt_id) <= 100 or not 0 <= payload.page <= 100:
        raise HTTPException(422, "Invalid progress")
    with db() as conn:
        init(conn)
        _, questions = load_exam(conn,exam_id,user)
        allowed = {str(q["id"]) for q in questions}
        if not set(payload.answers).issubset(allowed) or any(not isinstance(v,str) or len(v)>500 for v in payload.answers.values()):
            raise HTTPException(422, "Invalid answers")
        if conn.execute("SELECT 1 FROM standard_attempts WHERE student_id=? AND publication_id=? AND attempt_id=?", (user["id"],exam_id,payload.attempt_id)).fetchone():
            raise HTTPException(409, "This attempt has already been submitted")
        conn.execute("INSERT INTO standard_progress(student_id,publication_id,attempt_id,answers,page,updated_at) VALUES (?,?,?,?,?,?) ON CONFLICT(student_id,publication_id) DO UPDATE SET attempt_id=excluded.attempt_id,answers=excluded.answers,page=excluded.page,updated_at=excluded.updated_at", (user["id"],exam_id,payload.attempt_id,json.dumps(payload.answers),payload.page,datetime.now(timezone.utc).isoformat()))
    return {"saved":True}


@app.get("/api/standard/exams/{exam_id}")
def exam_detail(exam_id: str, user=Depends(current_user)):
    student(user)
    with db() as conn:
        init(conn)
        visible = conn.execute("SELECT active FROM standard_visibility WHERE publication_id=?", (exam_id,)).fetchone()
        progress=conn.execute("SELECT 1 FROM standard_progress WHERE student_id=? AND publication_id=?", (user["id"],exam_id)).fetchone()
        if (not visible or not visible["active"]) and not progress:
            raise HTTPException(404, "Exam is no longer available for new sessions")
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
        visibility=conn.execute("SELECT active FROM standard_visibility WHERE publication_id=?", (exam_id,)).fetchone()
        existing=conn.execute("SELECT attempt_id FROM standard_progress WHERE student_id=? AND publication_id=?", (user["id"],exam_id)).fetchone()
        if (not visibility or not visibility["active"]) and (not existing or existing["attempt_id"] != payload.attempt_id):
            raise HTTPException(403, "Only an already-started exam may be saved")
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
        conn.execute("DELETE FROM standard_progress WHERE student_id=? AND publication_id=?", (user["id"],exam_id))
        return {"score":score,"maximum":len(questions),"already_submitted":False}

@app.get("/api/standard/my-attempts")
def standard_my_attempts(user=Depends(current_user)):
    student(user)
    with db() as conn:
        init(conn)
        return [dict(r) for r in conn.execute("SELECT publication_id,score,maximum,submitted_at FROM standard_attempts WHERE student_id=? ORDER BY id DESC", (user["id"],))]
