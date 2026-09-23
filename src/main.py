import json
from src.config import PROJECT_ROOT
from src.llm_client import chat
from src.tool import KB_TOOL
from src.kb_retriever import retrieve
from src.reformulator import reformulate
from src.escalation_routing import route, RoutingDecision
from src.sanitize import clean, scan

_PRIMARY = (PROJECT_ROOT / "prompts" / "primary_persona.txt").read_text()
_FALLBACK = (PROJECT_ROOT / "prompts" / "fallback_persona.txt").read_text()


def _load_persona(use_fallback: bool, disable_tool_guidance: bool = False) -> str:
    text = _FALLBACK if use_fallback else _PRIMARY
    if disable_tool_guidance:
        # Experiment for R1: remove persona-level tool guidance.
        lines = text.splitlines()
        out, skip = [], False
        for ln in lines:
            if ln.strip().startswith("# TOOL USE"):
                skip = True
                continue
            if skip and ln.startswith("# "):
                skip = False
            if not skip:
                out.append(ln)
        text = "\n".join(out)
    return text


def _derive_strategy(customer_message: str, conversation_history: list) -> str:
    text = customer_message.lower()
    forward_markers = [
        "just tell me", "just fix", "how do i", "what do i need",
        "skip", "get to the point", "stop apologizing",
    ]
    if any(m in text for m in forward_markers):
        return "next_step_first"
    return "acknowledge_first"


def _derive_stage(conversation_history: list) -> str:
    turns = sum(1 for m in conversation_history if m["role"] == "user")
    if turns <= 2:
        return "first_contact"
    if turns <= 5:
        return "established"
    return "wrapping_up"


def respond(
    routing: RoutingDecision,
    session_language: str,
    conversation_history: list,
    customer_message: str,
    use_fallback: bool = False,
    disable_tool_guidance: bool = False,
    force_strategy: str | None = None,
    force_stage: str | None = None,
) -> dict:
    if routing.target != "ARIA":
        return {
            "reply": None,
            "tool_called": False,
            "tool_args": None,
            "raw_internal": None,
            "leaked_tokens": [],
            "routed_to": routing.target,
            "escalation_category": routing.category,
            "persona": "fallback" if use_fallback else "primary",
            "strategy": None,
            "stage": None,
        }

    strategy = force_strategy or _derive_strategy(customer_message, conversation_history)
    stage = force_stage or _derive_stage(conversation_history)

    system = (
        _load_persona(use_fallback, disable_tool_guidance)
        .replace("{session_language}", session_language)
        .replace("{strategy}", strategy)
        .replace("{stage}", stage)
    )

    messages = [{"role": "system", "content": system}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": customer_message})

    resp = chat(messages, tools=[KB_TOOL])
    msg = resp.choices[0].message

    tool_called = False
    tool_args = None
    raw_internal = None

    if msg.tool_calls:
        tool_called = True
        call = msg.tool_calls[0]
        try:
            args = json.loads(call.function.arguments)
        except json.JSONDecodeError:
            args = {"query": ""}
        tool_args = args

        reformulated = reformulate(customer_message)
        result = retrieve(reformulated)
        raw_internal = result.get("internal")

        # Append the assistant's tool-call message and the tool result.
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }],
        })
        # ONLY customer_safe enters the conversation.
        messages.append({
            "role": "tool",
            "tool_call_id": call.id,
            "content": json.dumps({"policy": result["customer_safe"]}),
        })

        resp2 = chat(messages, tools=[KB_TOOL])
        msg = resp2.choices[0].message

    reply_raw = msg.content or ""
    leaked = scan(reply_raw)
    reply_clean = clean(reply_raw)

    return {
        "reply": reply_clean,
        "tool_called": tool_called,
        "tool_args": tool_args,
        "raw_internal": raw_internal,
        "leaked_tokens": leaked,
        "routed_to": "ARIA",
        "escalation_category": None,
        "persona": "fallback" if use_fallback else "primary",
        "strategy": strategy,
        "stage": stage,
    }


def run_turn(
    session_language: str,
    conversation_history: list,
    customer_message: str,
    use_fallback: bool = False,
    disable_tool_guidance: bool = False,
    force_strategy: str | None = None,
    force_stage: str | None = None,
) -> dict:
    routing = route(customer_message, conversation_history)
    out = respond(
        routing=routing,
        session_language=session_language,
        conversation_history=conversation_history,
        customer_message=customer_message,
        use_fallback=use_fallback,
        disable_tool_guidance=disable_tool_guidance,
        force_strategy=force_strategy,
        force_stage=force_stage,
    )
    out["routing_source"] = routing.source
    out["routing_confidence"] = routing.confidence
    return out