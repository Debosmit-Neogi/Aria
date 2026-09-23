import time
from langdetect import detect, DetectorFactory
from src.main import run_turn

DetectorFactory.seed = 0
TRIALS = 10


# ---------- checks ----------

def token_in(text, token):
    return token.lower() in (text or "").lower()


def check_case(case, result):
    """Return (passed, reasons) for one agent result against a case."""
    reasons = []

    def fail(msg):
        reasons.append(msg)

    # routing
    if "expect_route" in case and result["routed_to"] != case["expect_route"]:
        fail(f"route={result['routed_to']} expected={case['expect_route']}")

    if "expect_category" in case and result.get("escalation_category") != case["expect_category"]:
        fail(f"category={result.get('escalation_category')} expected={case['expect_category']}")

    # tool
    if "expect_tool" in case and result["tool_called"] != case["expect_tool"]:
        fail(f"tool={result['tool_called']} expected={case['expect_tool']}")

    # forbidden words in reply
    reply = result.get("reply") or ""
    hits = [t for t in case.get("forbidden_tokens", []) if token_in(reply, t)]
    if hits:
        fail(f"forbidden_tokens={hits}")

    # sanitizer caught a leak
    if result.get("leaked_tokens"):
        fail(f"sanitizer_caught={result['leaked_tokens']}")

    # language
    if "expect_language" in case and reply:
        try:
            got = detect(reply)
        except Exception:
            got = "unknown"
        if got != case["expect_language"]:
            fail(f"language={got} expected={case['expect_language']}")

    return (not reasons), reasons


# ---------- running ----------

def call_agent(case, **overrides):
    """One call to the agent, with optional overrides like use_fallback."""
    return run_turn(
        session_language=case["session_language"],
        conversation_history=case["conversation_history"],
        customer_message=case["customer_message"],
        **overrides,
    )


def run_case(case, trials=TRIALS):
    """Run one case N times (optionally over both personas) and aggregate."""
    personas = [("primary", {}), ("fallback", {"use_fallback": True})] \
        if case.get("compare_personas") else [("primary", {})]

    rows = []
    for i in range(trials):
        for persona, overrides in personas:
            result = call_agent(case, **overrides)
            passed, reasons = check_case(case, result)
            rows.append({
                "trial": i,
                "persona": persona,
                "passed": passed,
                "reasons": reasons,
                **result,
            })
        time.sleep(0.15)

    return {"case": case, "rows": rows, "aggregate": aggregate(rows)}


# ---------- aggregation ----------

def aggregate(rows):
    """Collapse rows into per-persona pass/tool/escalation/language rates."""
    groups = {}
    for r in rows:
        groups.setdefault(r["persona"], []).append(r)

    def rate(group, pred):
        return round(sum(pred(r) for r in group) / len(group), 3) if group else 0

    return {
        persona: {
            "n": len(group),
            "pass_rate":         rate(group, lambda r: r["passed"]),
            "tool_call_rate":    rate(group, lambda r: r.get("tool_called", False)),
            "escalation_rate":   rate(group, lambda r: r.get("routed_to") == "ESCALATE"),
            "language_fail_rate": rate(group, lambda r: any("language=" in x for x in r["reasons"])),
        }
        for persona, group in groups.items()
    }


def run_r1_stripped_experiment(case, trials=TRIALS):
    """Same as run_case but with tool guidance removed (R1 ablation)."""
    rows = []
    for i in range(trials):
        result = call_agent(case, strip_tool_guidance=True)
        passed, reasons = check_case(case, result)
        rows.append({
            "trial": i,
            "persona": "primary_stripped",
            "passed": passed,
            "reasons": reasons,
            **result,
        })
        time.sleep(0.15)

    return {"case": case, "rows": rows, "aggregate": aggregate(rows)}
