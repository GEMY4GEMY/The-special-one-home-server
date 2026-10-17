"""Balanced draft exam selection, without repeating question IDs."""
import secrets
from collections import defaultdict

ALLOWED_SIZES = (20, 40, 60, 80, 100)

def choose_questions(rows, count):
    if count not in ALLOWED_SIZES:
        raise ValueError("Unsupported exam size")
    if len(rows) < count:
        raise ValueError("Not enough questions")
    groups = defaultdict(list)
    for item in rows:
        groups[(item["kind"], item["difficulty"])].append(item["id"])
    rng = secrets.SystemRandom()
    for ids in groups.values():
        rng.shuffle(ids)
    selected = []
    while len(selected) < count:
        keys = [key for key in groups if groups[key]]
        rng.shuffle(keys)
        for key in keys:
            if len(selected) >= count:
                break
            selected.append(groups[key].pop())
    rng.shuffle(selected)
    return selected
