"""Student practice generated from the approved question bank."""
import json
import secrets
from fastapi import Depends, HTTPException
from pydantic import BaseModel
from backend.app import app, db, current_user
from backend.standard_exams import student, init, normalize
from backend.question_selection import choose_questions

class PracticeConfig(BaseModel):
    units: list[str]
    kinds: list[str]
    count: int = 20

@app.get("/api/standard/practice-filters")
def practice_filters(user=Depends(current_user)):
    student(user)
    with db() as conn:
        init(conn)
        profile=conn.execute("SELECT grade FROM students WHERE user_id=?",(user["id"],)).fetchone()
        if not profile: raise HTTPException(403,"Student profile missing")
        rows=conn.execute("SELECT unit,kind,COUNT(*) AS total FROM question_bank WHERE grade=? GROUP BY unit,kind",(profile["grade"],)).fetchall()
        return {"grade":profile["grade"],"filters":[dict(x) for x in rows]}

@app.post("/api/standard/practice-create")
def practice_create(payload:PracticeConfig,user=Depends(current_user)):
    student(user)
    if payload.count not in (20,40,60,80,100) or not payload.units or not payload.kinds or any(x not in ("choose","fill","rearrange","letters") for x in payload.kinds):
        raise HTTPException(422,"Invalid practice settings")
    if len(payload.units)>50 or len(payload.kinds)>4:
        raise HTTPException(422,"Too many filters")
    with db() as conn:
        init(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS standard_practice (id TEXT PRIMARY KEY,student_id INTEGER,question_ids TEXT)")
        grade=conn.execute("SELECT grade FROM students WHERE user_id=?",(user["id"],)).fetchone()
        if not grade: raise HTTPException(403,"Student profile missing")
        u=",".join("?" for _ in payload.units)
        k=",".join("?" for _ in payload.kinds)
        rows=conn.execute(f"SELECT id,kind,difficulty FROM question_bank WHERE grade=? AND unit IN ({u}) AND kind IN ({k})",(grade["grade"],*payload.units,*payload.kinds)).fetchall()
        if len(rows)<payload.count: raise HTTPException(422,f"Only {len(rows)} matching questions")
        try: ids=choose_questions(rows,payload.count)
        except ValueError as e: raise HTTPException(422,str(e))
        pid=secrets.token_urlsafe(18)
        conn.execute("INSERT INTO standard_practice VALUES (?,?,?)",(pid,user["id"],json.dumps(ids)))
        return {"id":pid,"question_count":len(ids)}

class PracticeSubmission(BaseModel):
    attempt_id: str
    answers: dict[str,str]

def get_private_questions(conn, practice_id, user):
    row=conn.execute("SELECT question_ids FROM standard_practice WHERE id=? AND student_id=?",(practice_id,user["id"])).fetchone()
    if not row: raise HTTPException(404,"Practice not found")
    ids=json.loads(row["question_ids"])
    questions=conn.execute("SELECT * FROM question_bank WHERE id IN ("+",".join("?" for _ in ids)+")",ids).fetchall()
    by_id={str(q["id"]):q for q in questions}
    if len(by_id)!=len(ids): raise HTTPException(409,"Questions unavailable")
    return [by_id[str(i)] for i in ids]

@app.get("/api/standard/practice/{practice_id}")
def get_practice(practice_id:str,user=Depends(current_user)):
    student(user)
    with db() as conn:
        init(conn)
        questions=get_private_questions(conn,practice_id,user)
        return {"id":practice_id,"title":"Custom practice","questions":[{"id":str(q["id"]),"type":q["kind"],"prompt":q["prompt"],"options":json.loads(q["options"] or "[]")} for q in questions]}

@app.post("/api/standard/practice/{practice_id}/submit")
def submit_practice(practice_id:str,payload:PracticeSubmission,user=Depends(current_user)):
    student(user)
    if not 8<=len(payload.attempt_id)<=100: raise HTTPException(422,"Invalid attempt ID")
    with db() as conn:
        init(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS standard_practice_results (id INTEGER PRIMARY KEY,student_id INTEGER,practice_id TEXT,attempt_id TEXT,score INTEGER,maximum INTEGER,submitted_at TEXT,UNIQUE(student_id,attempt_id))")
        questions=get_private_questions(conn,practice_id,user)
        valid_ids={str(q["id"]) for q in questions}
        if not set(payload.answers).issubset(valid_ids): raise HTTPException(422,"Unknown question ID")
        if any(not isinstance(v,str) or len(v)>500 for v in payload.answers.values()): raise HTTPException(422,"Invalid answer")
        previous=conn.execute("SELECT practice_id,score,maximum FROM standard_practice_results WHERE student_id=? AND attempt_id=?",(user["id"],payload.attempt_id)).fetchone()
        if previous:
            if previous["practice_id"]!=practice_id: raise HTTPException(409,"Attempt ID already used")
            return {"score":previous["score"],"maximum":previous["maximum"],"already_submitted":True}
        score=sum(normalize(payload.answers.get(str(q["id"]),""))==normalize(q["answer"]) for q in questions)
        from datetime import datetime,timezone
        conn.execute("INSERT INTO standard_practice_results(student_id,practice_id,attempt_id,score,maximum,submitted_at) VALUES (?,?,?,?,?,?)",(user["id"],practice_id,payload.attempt_id,score,len(questions),datetime.now(timezone.utc).isoformat()))
        return {"score":score,"maximum":len(questions),"already_submitted":False}

@app.get("/api/standard/practice-results")
def practice_results(user=Depends(current_user)):
    student(user)
    with db() as conn:
        init(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS standard_practice_results (id INTEGER PRIMARY KEY,student_id INTEGER,practice_id TEXT,attempt_id TEXT,score INTEGER,maximum INTEGER,submitted_at TEXT,UNIQUE(student_id,attempt_id))")
        return [dict(r) for r in conn.execute("SELECT practice_id,score,maximum,submitted_at FROM standard_practice_results WHERE student_id=? ORDER BY id DESC",(user["id"],))]
