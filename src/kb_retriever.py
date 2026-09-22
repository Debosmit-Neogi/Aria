import json
from pathlib import Path

_KB_PATH = Path("data/kb.json")
_KB = json.loads(_KB_PATH.read_text())

def retrieve(query: str) -> dict:
    q = (query or "").lower()
    for entry in _KB["entries"]:
        if any(k in q for k in entry["keys"]):
            return entry
    return _KB["fallback"]
