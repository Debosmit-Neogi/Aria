## routing to specialist in case of escalation
from dataclasses import dataclass
from src.escalation_detector import detect

_ESCALATION_CATEGORIES = {"personal_danger", "legal", "fraud"}


@dataclass(frozen=True)
class RoutingDecision:
    target: str           # "ARIA" or "ESCALATE"
    category: str | None  # escalation category if target == "ESCALATE"
    confidence: float
    source: str
    _token: str = "route-issued"

    def __post_init__(self):
        if self._token != "route-issued":
            raise ValueError("RoutingDecision must be issued by route().")


def route(customer_message: str, conversation_history: list) -> RoutingDecision:
    result = detect(customer_message, conversation_history)
    cat = result["category"]
    if cat in _ESCALATION_CATEGORIES:
        return RoutingDecision(
            target="ESCALATE",
            category=cat,
            confidence=result.get("confidence", 0.0),
            source=result.get("source", "unknown"),
        )
    return RoutingDecision(
        target="ARIA",
        category=None,
        confidence=1.0,
        source="router",
    )
