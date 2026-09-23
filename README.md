# Aria

LLM-driven support persona with a two-source prompt design (primary + fallback),
a native knowledge-base retrieval tool, an escalation router that runs ahead of
Aria, and a self-built test harness covering six risk areas (R1–R6).

Model: `openai/gpt-oss-120b` via Groq's OpenAI-compatible chat completions API.

---

## 1. Setup and Run

### Prerequisites

- Python 3.11 or newer (3.12 recommended; 3.14 works but some wheels are still
  catching up)
- A Groq API key (sandbox/dev tier is enough — never use a production key)

### Install

```bash
# from the project root
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Edit `.env` and set your key:

```
GROQ_API_KEY=your_dev_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

`.env` is gitignored. Never commit it.

Verify the key is loaded:

```bash
python -c "from src.config import GROQ_API_KEY, GROQ_MODEL; print('key set:', bool(GROQ_API_KEY)); print('model:', GROQ_MODEL)"
```

Expected:

```
key set: True
model: openai/gpt-oss-120b
```

### Run the full test suite

```bash
python test_run.py
```

This runs every case in `tests/cases.py` at the trial count specified per case
(5 trials for R1, R4, R5 and the R6 classifier case; 3 trials elsewhere), plus
the R1 ablation that strips persona-level tool guidance. Progress prints per
trial and per case. Results are written incrementally so a mid-run interruption
does not lose completed cases.

Two files are written under `results_<timestamp>/`:

- `raw_results_<timestamp>.jsonl` — one JSON object per case with per-trial
  rows and an aggregate block.
- `summary_<timestamp>.json` — aggregate pass/tool/escalation/language-fail
  rates per case.

### Known operational limits

The Groq free tier caps usage at **200,000 tokens per day (TPD)** for
`openai/gpt-oss-120b`. A full 10-trial run of the complete suite exceeds this
budget. Two completed runs are included in this repository:

- `results_trial3/` — every case at 3 trials.
- `results_trial3-5/` — 5 trials for R1/R4/R5 and the R6 classifier case,
  3 trials elsewhere; truncated when the TPD cap was reached (see that run's
  `summary_*.json` for the recorded `RateLimitError`).

To reproduce the combined dataset in the self-audit, run both and merge. To run
a lighter pass, lower `TRIALS` in `tests/harnessing.py` or the per-case
`"trials"` overrides in `tests/cases.py`.

---

## 2. File Structure

```
.
├── .env                     Local secrets (gitignored). Copy from .env.example.
├── .env.example             Template with variable names, no values.
├── .gitignore               Excludes .env, __pycache__, venv, results.
├── README.md                This file.
├── requirements.txt         Runtime dependencies.
├── Task5.md                 Written self-audit (R1–R6).
├── test_run.py              Entry point. Runs the full test suite.
│
├── data/
│   └── kb.json              Mock knowledge base. Each entry has `keys` for
│                            matching, an `internal` block (severity,
│                            dispute_type, ref_id — never customer-facing),
│                            and a `customer_safe` policy string.
│
├── prompts/
│   ├── primary_persona.txt  Main Aria system prompt: identity, tone,
│   │                        specificity, response shape, address
│   │                        boundaries, language rule, tool-use guidance,
│   │                        internal-info rule, safety note.
│   ├── fallback_persona.txt Independently written second source used only
│   │                        when the primary is unavailable. Must cover
│   │                        every rule the primary does (R4/R5 grade this).
│   └── reformulation.txt    Pre-retrieval prompt. Rewrites the customer
│                            message into internal KB search vocabulary.
│
├── results_trial3/          Run 1 output (3 trials per case).
│   ├── raw_results_*.jsonl  Per-trial rows + per-case aggregates.
│   └── summary_*.json       Aggregate summary only.
│
├── results_trial3-5/        Run 2 output (5 trials where budget allowed).
│   ├── raw_results_*.jsonl  Same format. Contains recorded 429s where the
│   │                        run was cut short.
│   └── summary_*.json       Same format.
│
├── src/
│   ├── __init__.py          Marks `src` as a package.
│   ├── config.py            Loads .env, defines PROJECT_ROOT, GROQ_API_KEY,
│   │                        GROQ_MODEL, BASE_URL, TEMPERATURE.
│   ├── llm_client.py        Thin wrapper over OpenAI-compatible Groq client.
│   │                        Single `chat()` helper used everywhere.
│   ├── kb_retriever.py      Loads data/kb.json and exposes `retrieve(query)`.
│   │                        Returns the full entry (internal + customer_safe).
│   ├── tool.py              Defines KB_TOOL, the OpenAI function-calling
│   │                        schema exposed to the model. Name: lookup_policy.
│   ├── reformulator.py      Calls the reformulation prompt and returns the
│   │                        internal search query string.
│   ├── escalation_detector.py
│   │                        Safety detector. Regex fast-path for legal/fraud/
│   │                        personal-danger phrases, plus an LLM classifier
│   │                        for messages the regex does not match.
│   ├── escalation_routing.py
│   │                        `route()` returns a RoutingDecision dataclass
│   │                        whose _token guard prevents external construction.
│   │                        `Aria.respond()` requires this object.
│   ├── sanitize.py          Defense-in-depth scan on final replies. Replaces
│   │                        SEV-*, KB-*-*, BILLING-*, PLATFORM-*, TICKET-*
│   │                        patterns if any reach the customer-facing text.
│   └── main.py              Turn orchestration: route → load persona →
│                            substitute {session_language}/{strategy}/{stage} →
│                            call model → handle tool calls → sanitize →
│                            return structured result dict.
│
└── tests/
    ├── __init__.py          Marks `tests` as a package.
    ├── cases.py             Test case definitions. Each case declares risk
    │                        area (R1–R6), session_language, conversation
    │                        history, customer message, expected route/tool/
    │                        language, forbidden tokens, compare_personas
    │                        flag, and optional per-case `trials` override.
    ├── harnessing.py        Harness internals: call_agent, run_case,
    │                        run_r1_stripped_experiment, check_case,
    │                        aggregate. Reads per-case `trials` override.
    └── run.py               Suite runner. Iterates cases, runs each,
                             writes raw JSONL incrementally, updates the
                             summary after every case, isolates failures
                             per case so one bad run does not kill the suite.
```


### Results directories are committed intentionally

Both `results_trial3/` and `results_trial3-5/` are checked in so the raw
per-trial evidence behind `Task5.md` is reproducible without re-running the
suite against a rate-limited API key. They are small enough to ship and are
the exact files the self-audit cites.
