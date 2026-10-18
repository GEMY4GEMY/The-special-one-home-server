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
    if not 1<=payload.count<=100 or not payload.units or not payload.kinds or any(x not in ("choose","fill","rearrange","letters") for x in payload.kinds):
        raise HTTPException(422,"Invalid practice settings")
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
