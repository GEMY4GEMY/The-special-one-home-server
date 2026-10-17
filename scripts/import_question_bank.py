"""Import teacher-reviewed question bank JSON into the offline Standard database.

Run while the server is stopped:
  runtime\\python.exe scripts\\import_question_bank.py path\\to\\questions.json
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

ALLOWED_KINDS = {"choose", "fill", "rearrange", "letters"}
ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}


def validate(raw):
    if not isinstance(raw, dict) or raw.get("format") != "the-special-one-question-bank" or raw.get("version") != 1:
        raise ValueError("Unsupported question-bank file format/version")
    questions = raw.get("questions")
    if not isinstance(questions, list) or not questions or len(questions) > 10000:
        raise ValueError("questions must contain 1 to 10000 entries")
    clean = []
    for number, item in enumerate(questions, 1):
        if not isinstance(item, dict):
            raise ValueError(f"Question {number}: expected an object")
        fields = ("grade", "unit", "lesson", "difficulty", "kind", "prompt", "answer")
        if any(not isinstance(item.get(k), str) or not item[k].strip() for k in fields):
            raise ValueError(f"Question {number}: missing or invalid field")
        if item["kind"] not in ALLOWED_KINDS or item["difficulty"] not in ALLOWED_DIFFICULTIES:
            raise ValueError(f"Question {number}: unsupported kind or difficulty")
        if len(item["prompt"]) > 1000 or len(item["answer"]) > 300:
            raise ValueError(f"Question {number}: text too long")
        options = item.get("options", [])
        if not isinstance(options, list) or any(not isinstance(x, str) for x in options):
            raise ValueError(f"Question {number}: invalid options")
        if item["kind"] == "choose" and (not 2 <= len(options) <= 5 or item["answer"] not in options):
            raise ValueError(f"Question {number}: answer must be among 2-5 options")
        clean.append(tuple(item[k].strip() for k in fields) + (json.dumps(options, ensure_ascii=False),))
    return clean


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: import_question_bank.py questions.json")
    source = Path(sys.argv[1])
    rows = validate(json.loads(source.read_text(encoding="utf-8-sig")))
    root = Path(__file__).resolve().parent.parent
    database = Path(os.getenv("TSO_DB_PATH", str(root / "backend" / "data" / "standard.sqlite3")))
    if not database.exists():
        raise SystemExit("Standard database missing. Start the Standard server once, then close it.")
    with sqlite3.connect(database, timeout=10) as db:
        db.execute("CREATE TABLE IF NOT EXISTS question_bank (id INTEGER PRIMARY KEY, grade TEXT, unit TEXT, lesson TEXT, difficulty TEXT, kind TEXT, prompt TEXT, answer TEXT, options TEXT)")
        db.executemany("INSERT INTO question_bank (grade,unit,lesson,difficulty,kind,prompt,answer,options) VALUES (?,?,?,?,?,?,?,?)", rows)
    print(f"Imported {len(rows)} questions into {database}")


if __name__ == "__main__":
    main()
