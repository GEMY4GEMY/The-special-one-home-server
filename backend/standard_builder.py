"""Admin exam builder with grade, units and question-type filters."""
import json
import secrets
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from backend.app import app, db, admin_only, init_question_tables
from backend.question_selection import choose_questions
from backend.standard_exams import init as init_standard_exams

KINDS={"choose","fill","rearrange","letters"}

class BuildRequest(BaseModel):
    title: str = Field(min_length=3,max_length=150)
    grade: str = Field(min_length=1,max_length=80)
    units: list[str] = Field(min_length=1,max_length=50)
    kinds: list[str] = Field(min_length=1,max_length=4)
    count: int = Field(ge=1,le=100)

def init_visibility(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS standard_visibility (publication_id TEXT PRIMARY KEY, active INTEGER NOT NULL DEFAULT 0)")

@app.get("/api/admin/standard/filters")
def available_filters(user=Depends(admin_only)):
    with db() as conn:
        init_question_tables(conn)
        rows=conn.execute("SELECT grade,unit,kind,COUNT(*) AS total FROM question_bank GROUP BY grade,unit,kind ORDER BY grade,unit,kind").fetchall()
        return [dict(row) for row in rows]

@app.post("/api/admin/standard/build")
def build_exam(payload:BuildRequest,user=Depends(admin_only)):
    if any(kind not in KINDS for kind in payload.kinds):
        raise HTTPException(422,"Unsupported question type")
    units=list(dict.fromkeys(x.strip() for x in payload.units if x.strip()))
    kinds=list(dict.fromkeys(payload.kinds))
    if not units:
        raise HTTPException(422,"Choose at least one unit")
    placeholders=",".join("?" for _ in units)
    kindholders=",".join("?" for _ in kinds)
    with db() as conn:
        init_question_tables(conn)
        rows=conn.execute(f"SELECT id,kind,difficulty FROM question_bank WHERE grade=? AND unit IN ({placeholders}) AND kind IN ({kindholders})",(payload.grade,*units,*kinds)).fetchall()
        if len(rows)<payload.count:
            raise HTTPException(422,f"Only {len(rows)} matching questions available; requested {payload.count}")
        try:
            selected=choose_questions(rows,payload.count)
        except ValueError as exc:
            raise HTTPException(422,str(exc))
        draft_id=secrets.token_urlsafe(18)
        conn.execute("INSERT INTO exam_drafts(id,title,grade,question_ids) VALUES (?,?,?,?)",(draft_id,payload.title,payload.grade,json.dumps(selected)))
        return {"id":draft_id,"question_count":len(selected),"grade":payload.grade,"units":units,"kinds":kinds,"status":"draft"}

@app.get("/api/admin/standard/visibility")
def visibility(user=Depends(admin_only)):
    with db() as conn:
        init_question_tables(conn)
        init_standard_exams(conn)
        init_visibility(conn)
        return [dict(r) for r in conn.execute("SELECT p.id,d.title,d.grade,COALESCE(v.active,0) AS active FROM standard_publications p JOIN exam_drafts d ON d.id=p.draft_id LEFT JOIN standard_visibility v ON v.publication_id=p.id ORDER BY p.published_at DESC")]

@app.post("/api/admin/standard/visibility/{publication_id}/{state}")
def set_visibility(publication_id:str,state:str,user=Depends(admin_only)):
    if state not in ("show","hide"):
        raise HTTPException(422,"Use show or hide")
    with db() as conn:
        init_question_tables(conn)
        init_standard_exams(conn)
        init_visibility(conn)
        row=conn.execute("SELECT p.id,d.grade FROM standard_publications p JOIN exam_drafts d ON d.id=p.draft_id WHERE p.id=?",(publication_id,)).fetchone()
        if not row:
            raise HTTPException(404,"Published exam not found")
        if state=="show":
            conn.execute("UPDATE standard_visibility SET active=0 WHERE publication_id IN (SELECT p.id FROM standard_publications p JOIN exam_drafts d ON d.id=p.draft_id WHERE d.grade=?)",(row["grade"],))
        conn.execute("INSERT INTO standard_visibility(publication_id,active) VALUES (?,?) ON CONFLICT(publication_id) DO UPDATE SET active=excluded.active",(publication_id,int(state=="show")))
        return {"id":publication_id,"active":state=="show","grade":row["grade"]}
