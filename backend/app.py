"""THE SPECIAL ONE local-only prototype. Not production-ready."""
import os
import sqlite3
import secrets
import hashlib
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pwdlib import PasswordHash

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("TSO_DB_PATH", str(ROOT / "data" / "local.sqlite3")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
ADMIN_USERNAME = os.environ.get("TSO_ADMIN_USERNAME", "Mrsameh")
password_hash = PasswordHash.recommended()
app = FastAPI(title="THE SPECIAL ONE Home Server", docs_url=None, redoc_url=None)
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
    with db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE NOT NULL REFERENCES users(id), student_code TEXT UNIQUE NOT NULL, full_name TEXT NOT NULL, grade TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS results (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES students(id), exam_title TEXT NOT NULL, score REAL NOT NULL, maximum REAL NOT NULL, created_at TEXT NOT NULL)")
        conn.execute("PRAGMA foreign_keys = ON")
        existing = conn.execute("SELECT id FROM users WHERE username=?", (ADMIN_USERNAME,)).fetchone()
        if not existing:
            initial = os.environ.get("TSO_ADMIN_INITIAL_PASSWORD")
            if not initial:
                raise RuntimeError("Set TSO_ADMIN_INITIAL_PASSWORD before first startup; never commit it.")
            conn.execute("INSERT INTO users(username,password_hash,role) VALUES (?,?,?)", (ADMIN_USERNAME, password_hash.hash(initial), "admin"))

class Login(BaseModel):
    username: str
    password: str

class StudentCreate(BaseModel):
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
    return """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>THE SPECIAL ONE</title><style>body{font-family:system-ui;background:#eef3fa;margin:0;padding:3rem 1rem;color:#152c4b}.panel{max-width:500px;margin:auto;background:white;border-radius:18px;padding:2rem;box-shadow:0 8px 30px #0001}input,button{box-sizing:border-box;width:100%;padding:14px;margin:8px 0;border-radius:10px;border:1px solid #ccd5e0}button{background:#1556ad;color:white;font-weight:700;cursor:pointer}</style><main class="panel"><h1>THE SPECIAL ONE</h1><p>Home Server — Local Network</p><form id="login"><input name="username" placeholder="Username" autocomplete="username" required><input name="password" type="password" placeholder="Password" autocomplete="current-password" required><button>Sign in</button></form><div id="view" aria-live="polite"></div></main><script>document.querySelector('#login').onsubmit=async e=>{e.preventDefault();const f=e.target;const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:f.username.value,password:f.password.value})});if(!r.ok){document.querySelector('#view').textContent='Login failed';return}const me=await r.json();f.hidden=true;const v=document.querySelector('#view');v.textContent='Signed in as '+me.username+' ('+me.role+')';if(me.role==='student'){const res=await fetch('/api/my-results');const items=await res.json();const ul=document.createElement('ul');items.forEach(x=>{const li=document.createElement('li');li.textContent=x.exam_title+': '+x.score+' / '+x.maximum;ul.append(li)});v.append(ul)}};</script></html>"""
