"""Administrator overview of graded teacher exams and private practice."""
from fastapi import Depends, Query
from backend.app import app, db, admin_only
from backend.standard_exams import init

@app.get("/api/admin/standard/results")
def admin_standard_results(grade: str | None = Query(default=None, max_length=80), limit: int = Query(default=500, ge=1, le=50000), user=Depends(admin_only)):
    with db() as conn:
        init(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS standard_practice_results (id INTEGER PRIMARY KEY,student_id INTEGER,practice_id TEXT,attempt_id TEXT,score INTEGER,maximum INTEGER,submitted_at TEXT,UNIQUE(student_id,attempt_id))")
        teacher=conn.execute("""
            SELECT s.full_name,s.grade,u.username,d.title AS exam_title,
                   a.score,a.maximum,a.submitted_at,'teacher' AS exam_type
            FROM standard_attempts a
            JOIN users u ON u.id=a.student_id
            JOIN students s ON s.user_id=u.id
            JOIN standard_publications p ON p.id=a.publication_id
            JOIN exam_drafts d ON d.id=p.draft_id
        """).fetchall()
        practice=conn.execute("""
            SELECT s.full_name,s.grade,u.username,'Custom practice' AS exam_title,
                   a.score,a.maximum,a.submitted_at,'practice' AS exam_type
            FROM standard_practice_results a
            JOIN users u ON u.id=a.student_id
            JOIN students s ON s.user_id=u.id
        """).fetchall()
        rows=[dict(r) for r in teacher]+[dict(r) for r in practice]
        if grade is not None:
            rows=[r for r in rows if r["grade"]==grade]
        rows.sort(key=lambda x:x["submitted_at"],reverse=True)
        students=len({r["username"] for r in rows})
        return {"total":len(rows),"students":students,"teacher_attempts":len(teacher),"practice_attempts":len(practice),"results":rows[:limit]}
