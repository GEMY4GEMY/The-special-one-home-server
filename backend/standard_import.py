"""Validate offline question-bank JSON before writing any records."""
import json

FIELDS = ("grade", "unit", "lesson", "difficulty", "kind", "prompt", "answer")
KINDS = {"choose", "fill", "rearrange", "letters"}
DIFFICULTIES = {"easy", "medium", "hard"}

def validate_bank(payload):
    if not isinstance(payload, dict) or payload.get("format") != "the-special-one-question-bank" or payload.get("version") != 1:
        raise ValueError("Invalid question-bank format or version")
    items = payload.get("questions")
    if not isinstance(items, list) or not 1 <= len(items) <= 10000:
        raise ValueError("Expected 1 to 10000 questions")
    rows = []
    for i, q in enumerate(items, 1):
        if not isinstance(q, dict) or any(not isinstance(q.get(k), str) or not q[k].strip() for k in FIELDS):
            raise ValueError(f"Question {i}: missing required text")
        if q["kind"] not in KINDS or q["difficulty"] not in DIFFICULTIES:
            raise ValueError(f"Question {i}: invalid type or difficulty")
        if len(q["prompt"]) > 1000 or len(q["answer"]) > 300:
            raise ValueError(f"Question {i}: text too long")
        options = q.get("options", [])
        if not isinstance(options, list) or any(not isinstance(x, str) for x in options):
            raise ValueError(f"Question {i}: invalid options")
        if q["kind"] == "choose" and (not 2 <= len(options) <= 5 or q["answer"] not in options):
            raise ValueError(f"Question {i}: answer missing from choices")
        rows.append(tuple(q[k].strip() for k in FIELDS) + (json.dumps(options, ensure_ascii=False),))
    return rows
