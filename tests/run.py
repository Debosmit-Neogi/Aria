import json
import os
from datetime import datetime, timezone
from src.config import PROJECT_ROOT
from tests.cases import CASES
from tests.harnessing import (
    run_case,
    run_r1_stripped_experiment,
    TRIALS,
)

RESULTS_DIR = PROJECT_ROOT / "results"


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"raw_results_{ts}.jsonl"
    summary_path = RESULTS_DIR / f"summary_{ts}.json"

    summary = {}

    with open(out_path, "w", encoding="utf-8") as f:
        for case in CASES:
            print(f"[RUN] {case['id']} (risk {case['risk']})", flush=True)

            try:
                r = run_case(case, trials=TRIALS)
            except Exception as e:
                print(f"  [FAIL] {case['id']}: {type(e).__name__}: {e}", flush=True)
                # record the failure so the file reflects what happened
                f.write(json.dumps({
                    "case_id": case["id"],
                    "risk": case["risk"],
                    "case": case,
                    "error": f"{type(e).__name__}: {e}",
                    "aggregate": None,
                    "rows": [],
                }) + "\n")
                f.flush()
                summary[case["id"]] = {
                    "risk": case["risk"],
                    "error": f"{type(e).__name__}: {e}",
                }
                _write_summary(summary_path, summary)
                continue

            # write this case's block immediately
            f.write(json.dumps({
                "case_id": case["id"],
                "risk": case["risk"],
                "case": case,
                "aggregate": r["aggregate"],
                "rows": r["rows"],
            }) + "\n")
            f.flush()
            print(f"  [OK] {case['id']} -> {r['aggregate']}", flush=True)

            summary[case["id"]] = {
                "risk": case["risk"],
                "aggregate": r["aggregate"],
            }

            # R1 ablation
            if case.get("strip_tool_guidance_experiment"):
                print(f"  [R1 ablation] {case['id']} stripped", flush=True)
                try:
                    r2 = run_r1_stripped_experiment(case, trials=TRIALS)
                except Exception as e:
                    print(f"  [FAIL stripped] {case['id']}: {e}", flush=True)
                    continue
                f.write(json.dumps({
                    "case_id": case["id"] + "__stripped",
                    "risk": "R1",
                    "case": case,
                    "aggregate": r2["aggregate"],
                    "rows": r2["rows"],
                }) + "\n")
                f.flush()
                summary[case["id"] + "__stripped"] = {
                    "risk": "R1",
                    "aggregate": r2["aggregate"],
                }

            _write_summary(summary_path, summary)

    _write_summary(summary_path, summary)

    print(f"\nWrote {out_path}")
    print(f"Wrote {summary_path}")
    print("\n=== AGGREGATE SUMMARY ===")
    for cid, s in summary.items():
        print(f"{cid} [{s['risk']}]: {s.get('aggregate', s.get('error'))}")


def _write_summary(path, summary):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
