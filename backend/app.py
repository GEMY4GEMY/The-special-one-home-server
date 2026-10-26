"""THE SPECIAL ONE local-only prototype. Not production-ready."""
import os
import sqlite3
import secrets
import hashlib
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from pwdlib import PasswordHash

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("TSO_DB_PATH", str(ROOT / "data" / "local.sqlite3")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
ADMIN_USERNAME = os.environ.get("TSO_ADMIN_USERNAME", "Mrsameh")
password_hash = PasswordHash.recommended()
app = FastAPI(title="THE SPECIAL ONE Home Server", docs_url=None, redoc_url=None)
FRONTEND = ROOT.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")
sessions = {}

@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

@app.on_event("startup")
def initialize():
    if os.environ.get('TSO_EDITION') != 'standard':
        from backend.ai_queue import initialize as initialize_ai_queue
        initialize_ai_queue()
    with db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE NOT NULL REFERENCES users(id), student_code TEXT UNIQUE NOT NULL, full_name TEXT NOT NULL, grade TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS results (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES students(id), exam_title TEXT NOT NULL, score REAL NOT NULL, maximum REAL NOT NULL, created_at TEXT NOT NULL)")
        conn.execute("PRAGMA foreign_keys = ON")
        existing = conn.execute("SELECT id FROM users WHERE username=?", (ADMIN_USERNAME,)).fetchone()
        if not existing:
            initial = os.environ.get("TSO_ADMIN_INITIAL_PASSWORD")
            if not initial or len(initial) < 12:
                raise RuntimeError("Set TSO_ADMIN_INITIAL_PASSWORD (at least 12 characters) before first startup; never commit it.")
            conn.execute("INSERT INTO users(username,password_hash,role) VALUES (?,?,?)", (ADMIN_USERNAME, password_hash.hash(initial), "admin"))

class Login(BaseModel):
    username: str
    password: str

class StudentCreate(BaseModel):
    stage: str
    username: str
    password: str
    student_code: str
    full_name: str
    grade: str

class ResultCreate(BaseModel):
    student_code: str
    exam_title: str
    score: float
    maximum: float

def current_user(request: Request):
    token = request.cookies.get("tso_session", "")
    uid = sessions.get(hashlib.sha256(token.encode()).hexdigest())
    if uid is None:
        raise HTTPException(401, "Login required")
    with db() as conn:
        row = conn.execute("SELECT id,username,role FROM users WHERE id=?", (uid,)).fetchone()
    if row is None:
        raise HTTPException(401, "Login required")
    return dict(row)

def admin_only(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Forbidden")
    return user

@app.get("/health")
def health():
    return {"status": "ok", "service": "the-special-one", "port": 100}

@app.post("/api/login")
def login(payload: Login, response: Response):
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE username=?", (payload.username,)).fetchone()
    if not user or not password_hash.verify(payload.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    token = secrets.token_urlsafe(32)
    sessions[hashlib.sha256(token.encode()).hexdigest()] = user["id"]
    response.set_cookie("tso_session", token, httponly=True, samesite="strict", secure=False, max_age=28800)
    return {"username": user["username"], "role": user["role"]}

@app.post("/api/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("tso_session", "")
    sessions.pop(hashlib.sha256(token.encode()).hexdigest(), None)
    response.delete_cookie("tso_session")
    return {"ok": True}

@app.get("/api/me")
def me(user=Depends(current_user)):
    return user

@app.post("/api/students", status_code=201)
def create_student(payload: StudentCreate, user=Depends(admin_only)):
    if len(payload.password) < 10:
        raise HTTPException(400, "Student password must have at least 10 characters")
    allowed = {"Primary": 6, "Preparatory": 3, "Secondary": 3}
    if payload.stage not in allowed or payload.grade not in [f"{payload.stage} {i}" for i in range(1, allowed[payload.stage] + 1)]:
        raise HTTPException(422, "Select a valid stage and grade")
    try:
        with db() as conn:
            cur = conn.execute("INSERT INTO users(username,password_hash,role) VALUES (?,?,?)", (payload.username, password_hash.hash(payload.password), "student"))
            conn.execute("INSERT INTO students(user_id,student_code,full_name,grade) VALUES (?,?,?,?)", (cur.lastrowid, payload.student_code, payload.full_name, payload.grade))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Username or student code already exists")
    return {"student_code": payload.student_code}

@app.get("/api/students")
def students(user=Depends(admin_only)):
    with db() as conn:
        return [dict(x) for x in conn.execute("SELECT student_code,full_name,grade FROM students ORDER BY id DESC")]

@app.post("/api/results", status_code=201)
def add_result(payload: ResultCreate, user=Depends(admin_only)):
    if payload.maximum <= 0 or not 0 <= payload.score <= payload.maximum:
        raise HTTPException(400, "Invalid score")
    with db() as conn:
        student = conn.execute("SELECT id FROM students WHERE student_code=?", (payload.student_code,)).fetchone()
        if student is None:
            raise HTTPException(404, "Student not found")
        conn.execute("INSERT INTO results(student_id,exam_title,score,maximum,created_at) VALUES (?,?,?,?,?)", (student["id"], payload.exam_title, payload.score, payload.maximum, datetime.now(timezone.utc).isoformat()))
    return {"ok": True}

@app.get("/api/my-results")
def my_results(user=Depends(current_user)):
    if user["role"] != "student":
        raise HTTPException(403, "Student access only")
    with db() as conn:
        return [dict(x) for x in conn.execute("SELECT r.exam_title,r.score,r.maximum,r.created_at FROM results r JOIN students s ON s.id=r.student_id WHERE s.user_id=? ORDER BY r.id DESC", (user["id"],))]

@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse(FRONTEND / "index.html")


# Demonstration exam engine. Questions are illustrative, NOT from uploaded curricula.
class AnswerItem(BaseModel):
    question_id: str
    answer: str

class ExamSubmission(BaseModel):
    attempt_id: str
    answers: list[AnswerItem]

DEMO_QUESTIONS = [
    {"id": "d1", "type": "choose", "prompt": "Choose the correct word: I ___ a student.", "options": ["am", "is", "are"], "answer": "am"},
    {"id": "d2", "type": "rearrange", "prompt": "Rearrange the words: (school / go / I / to)", "tokens": ["school", "go", "I", "to"], "answer": "I go to school"},
    {"id": "d3", "type": "fill", "prompt": "Fill in the gap: She ___ happy. (is / are)", "answer": "is"},
    {"id": "d4", "type": "letters", "prompt": "Reorder the letters to make a word: P L A E P", "answer": "apple"},
]
DEMO_EXAM_ID = "demo-english-001"

@app.get("/api/exams")
def list_exams(user=Depends(current_user)):
    if user["role"] != "student":
        raise HTTPException(403, "Student access only")
    return [{"id": DEMO_EXAM_ID, "title": "English Skills — Demo Only", "question_count": len(DEMO_QUESTIONS), "demo": True}]

@app.get("/api/exams/{exam_id}")
def get_exam(exam_id: str, user=Depends(current_user)):
    if user["role"] != "student":
        raise HTTPException(403, "Student access only")
    if exam_id != DEMO_EXAM_ID:
        raise HTTPException(404, "Exam not found")
    return {"id": DEMO_EXAM_ID, "title": "English Skills — Demo Only", "demo": True,
            "questions": [{k: v for k, v in q.items() if k != "answer"} for q in DEMO_QUESTIONS]}

@app.post("/api/exams/{exam_id}/submit")
def submit_exam(exam_id: str, payload: ExamSubmission, user=Depends(current_user)):
    if user["role"] != "student":
        raise HTTPException(403, "Student access only")
    if exam_id != DEMO_EXAM_ID:
        raise HTTPException(404, "Exam not found")
    if not (8 <= len(payload.attempt_id) <= 100):
        raise HTTPException(400, "Invalid attempt ID")
    if len(payload.answers) > len(DEMO_QUESTIONS):
        raise HTTPException(400, "Too many answers")
    submitted = {}
    valid_ids = {q["id"] for q in DEMO_QUESTIONS}
    for item in payload.answers:
        if item.question_id not in valid_ids or item.question_id in submitted or len(item.answer) > 500:
            raise HTTPException(400, "Invalid or duplicate question")
        submitted[item.question_id] = item.answer
    def normalize(value):
        return " ".join(value.strip().casefold().split()).rstrip(".!?")
    score = sum(normalize(submitted.get(q["id"], "")) == normalize(q["answer"]) for q in DEMO_QUESTIONS)
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS exam_attempts
            (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, exam_id TEXT NOT NULL,
             attempt_id TEXT NOT NULL, score INTEGER NOT NULL, maximum INTEGER NOT NULL,
             created_at TEXT NOT NULL, UNIQUE(user_id, attempt_id))""")
        prior = conn.execute("SELECT exam_id,score,maximum FROM exam_attempts WHERE user_id=? AND attempt_id=?",
                             (user["id"], payload.attempt_id)).fetchone()
        if prior:
            if prior["exam_id"] != exam_id:
                raise HTTPException(409, "Attempt ID already used for another exam")
            return {"score": prior["score"], "maximum": prior["maximum"], "already_submitted": True}
        conn.execute("INSERT INTO exam_attempts(user_id,exam_id,attempt_id,score,maximum,created_at) VALUES (?,?,?,?,?,?)",
                     (user["id"], exam_id, payload.attempt_id, score, len(DEMO_QUESTIONS),
                      datetime.now(timezone.utc).isoformat()))
    return {"score": score, "maximum": len(DEMO_QUESTIONS), "already_submitted": False}

@app.get("/api/my-attempts")
def my_attempts(user=Depends(current_user)):
    if user["role"] != "student":
        raise HTTPException(403, "Student access only")
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS exam_attempts
            (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, exam_id TEXT NOT NULL,
             attempt_id TEXT NOT NULL, score INTEGER NOT NULL, maximum INTEGER NOT NULL,
             created_at TEXT NOT NULL, UNIQUE(user_id, attempt_id))""")
        return [dict(row) for row in conn.execute(
            "SELECT exam_id,score,maximum,created_at FROM exam_attempts WHERE user_id=? ORDER BY id DESC", (user["id"],))]

# Admin question bank and draft exam generator
import json
from backend.question_selection import choose_questions

class QuestionCreate(BaseModel):
    grade: str
    unit: str
    lesson: str
    difficulty: str
    kind: str
    prompt: str
    answer: str
    options: list[str] = []

class ExamDraftCreate(BaseModel):
    title: str
    grade: str
    count: int = 20

def init_question_tables(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS question_bank (id INTEGER PRIMARY KEY, grade TEXT, unit TEXT, lesson TEXT, difficulty TEXT, kind TEXT, prompt TEXT, answer TEXT, options TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS exam_drafts (id TEXT PRIMARY KEY, title TEXT, grade TEXT, question_ids TEXT)")

@app.post("/api/admin/question-bank")
def add_bank_question(payload: QuestionCreate, user=Depends(admin_only)):
    if payload.kind not in ("choose", "fill", "rearrange", "letters"):
        raise HTTPException(400, "Invalid question type")
    if payload.difficulty not in ("easy", "medium", "hard"):
        raise HTTPException(400, "Invalid difficulty")
    if not all(s.strip() for s in (payload.grade, payload.unit, payload.lesson, payload.prompt, payload.answer)):
        raise HTTPException(400, "Required field missing")
    if len(payload.prompt) > 1000 or len(payload.answer) > 300:
        raise HTTPException(400, "Text too long")
    if payload.kind == "choose" and (len(payload.options) < 2 or payload.answer not in payload.options):
        raise HTTPException(400, "Choose questions require valid options and answer")
    with db() as conn:
        init_question_tables(conn)
        cursor = conn.execute("INSERT INTO question_bank(grade,unit,lesson,difficulty,kind,prompt,answer,options) VALUES (?,?,?,?,?,?,?,?)", (payload.grade, payload.unit, payload.lesson, payload.difficulty, payload.kind, payload.prompt, payload.answer, json.dumps(payload.options)))
        return {"id": cursor.lastrowid}

@app.get("/api/admin/question-bank")
def list_bank_questions(grade: str = "", user=Depends(admin_only)):
    with db() as conn:
        init_question_tables(conn)
        rows = conn.execute("SELECT * FROM question_bank WHERE (? = '' OR grade = ?) ORDER BY id DESC LIMIT 500", (grade, grade)).fetchall()
        return [dict(row) for row in rows]

@app.post("/api/admin/exam-drafts")
def generate_exam_draft(payload: ExamDraftCreate, user=Depends(admin_only)):
    with db() as conn:
        init_question_tables(conn)
        rows = conn.execute("SELECT id,kind,difficulty FROM question_bank WHERE grade=?", (payload.grade,)).fetchall()
        try:
            selected = choose_questions(rows, payload.count)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        draft_id = secrets.token_urlsafe(18)
        conn.execute("INSERT INTO exam_drafts(id,title,grade,question_ids) VALUES (?,?,?,?)", (draft_id, payload.title, payload.grade, json.dumps(selected)))
        return {"id": draft_id, "question_count": len(selected), "status": "draft"}

@app.get("/api/admin/exam-drafts")
def list_exam_drafts(user=Depends(admin_only)):
    with db() as conn:
        init_question_tables(conn)
        rows=conn.execute("SELECT id,title,grade,question_ids FROM exam_drafts ORDER BY rowid DESC LIMIT 100").fetchall()
        return [{"id":r["id"],"title":r["title"],"grade":r["grade"],"question_count":len(json.loads(r["question_ids"]))} for r in rows]

@app.delete("/api/admin/question-bank/{question_id}")
def delete_bank_question(question_id: int, user=Depends(admin_only)):
    with db() as conn:
        init_question_tables(conn)
        drafts=conn.execute("SELECT question_ids FROM exam_drafts").fetchall()
        if any(question_id in json.loads(row["question_ids"]) for row in drafts):
            raise HTTPException(409,"Question is used in a saved draft")
        deleted=conn.execute("DELETE FROM question_bank WHERE id=?", (question_id,))
        if deleted.rowcount == 0:
            raise HTTPException(404,"Question not found")
        return {"deleted":question_id}

@app.put("/api/admin/question-bank/{question_id}")
def update_bank_question(question_id: int,payload: QuestionCreate,user=Depends(admin_only)):
    if payload.kind not in ("choose","fill","rearrange","letters") or payload.difficulty not in ("easy","medium","hard"):
        raise HTTPException(400,"Invalid type or difficulty")
    if not all(v.strip() for v in (payload.grade,payload.unit,payload.lesson,payload.prompt,payload.answer)):
        raise HTTPException(400,"Required field missing")
    if payload.kind=="choose" and (len(payload.options)<2 or payload.answer not in payload.options):
        raise HTTPException(400,"Invalid choice options")
    with db() as conn:
        init_question_tables(conn)
        drafts=conn.execute("SELECT question_ids FROM exam_drafts").fetchall()
        if any(question_id in json.loads(row["question_ids"]) for row in drafts):
            raise HTTPException(409,"Cannot modify a question used in a saved draft")
        changed=conn.execute("""UPDATE question_bank SET grade=?,unit=?,lesson=?,difficulty=?,kind=?,prompt=?,answer=?,options=? WHERE id=?""",
            (payload.grade,payload.unit,payload.lesson,payload.difficulty,payload.kind,payload.prompt,payload.answer,json.dumps(payload.options),question_id))
        if changed.rowcount == 0:
            raise HTTPException(404,"Question not found")
        return {"updated":question_id}

# Curriculum PDF import: text-only first stage. No AI generation or publication.
from fastapi import UploadFile, File
from backend.pdf_ingest import extract_pdf_pages

MAX_PDF_BYTES = 20 * 1024 * 1024

@app.post("/api/admin/pdf-inspect")
async def inspect_curriculum_pdf(file: UploadFile = File(...), user=Depends(admin_only)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "A PDF file is required")
    data = await file.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(413, "PDF exceeds 20 MB")
    try:
        pages = extract_pdf_pages(data)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {
        "filename": Path(file.filename).name,
        "page_count": len(pages),
        "text_pages": sum(bool(p["text"]) for p in pages),
        "image_pages": sum(p["needs_vision"] for p in pages),
        "pages": pages,
        "status": "inspection_only"
    }

from backend.local_ai import suggest_questions

class AIPageRequest(BaseModel):
    grade: str
    page_number: int
    page_text: str
    count: int = 5

@app.post("/api/admin/ai/suggest")
def ai_suggest(payload: AIPageRequest, user=Depends(admin_only)):
    if not payload.grade.strip() or not 1 <= payload.page_number <= 300 or len(payload.page_text) > 15000:
        raise HTTPException(422, "Invalid source page")
    try:
        questions = suggest_questions(payload.page_text, payload.page_number, payload.grade, payload.count)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except RuntimeError:
        raise HTTPException(503, "Local AI unavailable")
    return {"status": "pending_review", "questions": questions}

from backend.pdf_vision import read_visual_page

@app.post("/api/admin/pdf-vision")
async def inspect_pdf_visual(page_number: int, file: UploadFile = File(...), user=Depends(admin_only)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "PDF required")
    raw = await file.read(MAX_PDF_BYTES + 1)
    if len(raw) > MAX_PDF_BYTES:
        raise HTTPException(413, "PDF exceeds 20 MB")
    if not 1 <= page_number <= 300:
        raise HTTPException(422, "Invalid page number")
    try:
        return read_visual_page(raw, page_number)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except RuntimeError:
        raise HTTPException(503, "Local vision model unavailable")

from backend.ai_queue import submit as submit_ai_task, lookup as lookup_ai_task

@app.post("/api/admin/ai/suggest-async")
def ai_suggest_async(payload: AIPageRequest, user=Depends(admin_only)):
    if not payload.grade.strip() or not 1 <= payload.page_number <= 300 or len(payload.page_text) > 15000 or not 1 <= payload.count <= 10:
        raise HTTPException(422, "Invalid AI request")
    try:
        task_id = submit_ai_task(user["id"], suggest_questions, payload.page_text, payload.page_number, payload.grade, payload.count)
    except ValueError as exc:
        raise HTTPException(429, str(exc))
    return {"task_id": task_id, "state": "waiting"}

@app.get("/api/admin/ai/tasks/{task_id}")
def ai_task_status(task_id: str, user=Depends(admin_only)):
    task = lookup_ai_task(task_id, user["id"])
    if task is None:
        raise HTTPException(404, "Task not found")
    return task
