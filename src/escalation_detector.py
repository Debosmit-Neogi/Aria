import re
import json
from src.llm_client import chat

LEGAL = re.compile(
    r"\b(lawsuit|sue|suing|attorney|lawyer|legal action|litigation|court)\b",
    re.I,
)
FRAUD = re.compile(
    r"\b(chargeback|fraud|fraudulent|stolen card|unauthorized charge|dispute with my bank)\b",
    re.I,
)
DANGER = re.compile(
    r"\b(kill myself|suicide|suicidal|self[- ]harm|end my life|hurt myself|"
    r"don'?t want to (be here|live)|no reason to live)\b",
    re.I,
)

CLASSIFIER_PROMPT = """You are a safety classifier for a SaaS support system.
Read the customer message and the conversation history. Decide if the message
must be routed to a specialist rather than handled by the normal support agent.

Categories:
- "personal_danger": the message suggests the customer (or someone else) is in personal danger, including self-harm, suicidal ideation, or threats to life.
- "legal": the message contains a legal threat - lawsuit, attorney, litigation, formal legal action.
- "fraud": the message contains a fraud or chargeback threat - chargeback, unauthorized charge, stolen card, dispute with bank.
- "none": none of the above.

Return ONLY JSON: {"category": "<one of the four>", "confidence": <0.0-1.0>, "reason": "<short>"}
"""


def _regex_signal(text: str) -> str | None:
    if DANGER.search(text):
        return "personal_danger"
    if LEGAL.search(text):
        return "legal"
    if FRAUD.search(text):
        return "fraud"
    return None


def detect(customer_message: str, conversation_history: list) -> dict:
    """Return {"category": str, "confidence": float, "source": str}."""
    fast = _regex_signal(customer_message)
    if fast:
        return {"category": fast, "confidence": 0.9, "source": "regex"}

    history_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in conversation_history[-6:]
    )
    user_payload = (
        f"Conversation so far:\n{history_text or '(none)'}\n\n"
        f"Latest customer message:\n{customer_message}"
    )
    resp = chat(
        messages=[
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {"role": "user", "content": user_payload},
        ],
        temperature=0.0,
    )
    raw = resp.choices[0].message.content.strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Conservative fallback: if the classifier is unparseable, escalate.
        return {
            "category": "legal",
            "confidence": 0.0,
            "source": "classifier_parse_fail",
        }
    parsed["source"] = "classifier"
    return parsed
