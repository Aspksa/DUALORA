"""Local append-only (bounded) DUALORA diagnostic history; no network transfer."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json

LOG_PATH = Path.home() / "DUALORA" / "history.jsonl"
MAX_EVENTS = 500

def event_record(kind, detail, now=None):
    if kind not in ("scan", "layout", "mode", "connection", "error"):
        raise ValueError("Unsupported event type")
    return {"timestamp": (now or datetime.now(timezone.utc)).isoformat(),
            "type": kind, "detail": str(detail)[:400]}

def read_history(path=LOG_PATH):
    path = Path(path)
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines()[-MAX_EVENTS:]:
        try:
            value = json.loads(line)
            if isinstance(value, dict) and "type" in value:
                events.append(value)
        except json.JSONDecodeError:
            continue
    return events

def add_event(kind, detail, path=LOG_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    events = read_history(path)
    record = event_record(kind, detail)
    events.append(record)
    text = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in events[-MAX_EVENTS:])
    temporary = path.with_suffix(".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
    return record
