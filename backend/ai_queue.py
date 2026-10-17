"""In-memory worker for local curriculum processing."""
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from uuid import uuid4

executor = ThreadPoolExecutor(max_workers=1)
guard = Lock()
tasks = {}

def submit(owner, work, *args):
    with guard:
        if len(tasks) >= 100:
            raise ValueError("Task capacity reached")
        if sum(v["state"] in ("waiting", "working") for v in tasks.values()) >= 5:
            raise ValueError("Processing queue is full")
        key = uuid4().hex
        tasks[key] = {"owner": owner, "state": "waiting", "output": None}
    def runner():
        with guard:
            tasks[key]["state"] = "working"
        try:
            output = work(*args)
            with guard:
                tasks[key].update(state="complete", output=output)
        except Exception:
            with guard:
                tasks[key]["state"] = "failed"
    executor.submit(runner)
    return key

def lookup(key, owner):
    with guard:
        task = tasks.get(key)
        if task is None or task["owner"] != owner:
            return None
        return {"id": key, "state": task["state"], "output": task["output"]}
