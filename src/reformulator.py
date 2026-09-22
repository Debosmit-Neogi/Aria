from pathlib import Path
from src.llm_client import chat

_PROMPT = Path("prompts/reformulation.txt").read_text()

def reformulate(message: str) -> str:
    resp = chat(
        messages=[{"role": "user", "content": _PROMPT.format(message=message)}],
        temperature=0.0,
    )
    return resp.choices[0].message.content.strip()