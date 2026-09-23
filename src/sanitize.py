import re

INTERNAL_PATTERNS = [
    re.compile(r"\bSEV-\d+\b", re.I),
    re.compile(r"\bKB-[A-Z]+-\d+\b", re.I),
    re.compile(r"\bBILLING-[A-Z]+\b", re.I),
    re.compile(r"\bPLATFORM-[A-Z]+\b", re.I),
    re.compile(r"\bTICKET-\d+\b", re.I),
]

SAFE_REPLACEMENT = "a policy that applies here"


def scan(text: str) -> list:
    found = []
    for pat in INTERNAL_PATTERNS:
        found.extend(pat.findall(text or ""))
    return found


def clean(text: str) -> str:
    out = text or ""
    for pat in INTERNAL_PATTERNS:
        out = pat.sub(SAFE_REPLACEMENT, out)
    return out
