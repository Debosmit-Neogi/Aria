import json
import os
from datetime import datetime, timezone
from src.config import PROJECT_ROOT
from tests.cases import CASES
from tests.harnessing import (
    run_case,
    run_r1_stripped_experiment,
    TRIALS_DEFAULT,
)

RESULTS_DIR = PROJECT_ROOT / "results"


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"raw_results_{ts}.jsonl"
    summary_path = RESULTS_DIR / f"summary_{ts}.json"

    all_results = []
    summary = {}

    for case in CASES:
        print(f"[RUN] {case['id']} (risk {case['risk']})")
        r = run_case(case, trials=TRIALS_DEFAULT)
        all_results.append(r)
        summary[case["id"]] = {
            "risk": case["risk"],
            "aggregate": r["aggregate"],
        }

        if case.get("strip_tool_guidance_experiment"):
            print(
                f"  [R1 experiment] {case['id']} -- persona tool guidance stripped"
            )
            r2 = run_r1_stripped_experiment(case, trials=TRIALS_DEFAULT)
            all_results.append(r2)
            summary[case["id"] + "__stripped"] = {
                "risk": "R1",
                "aggregate": r2["aggregate"],
            }

    with open(out_path, "w", encoding="utf-8") as f:
        for block in all_results:
            f.write(json.dumps({
                "case_id": block["case"]["id"],
                "risk": block["case"]["risk"],
                "case": block["case"],
                "aggregate": block["aggregate"],
                "rows": block["rows"],
            }) + "\n")

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nWrote {out_path}")
    print(f"Wrote {summary_path}")

    print("\n=== AGGREGATE SUMMARY ===")
    for cid, s in summary.items():
        print(f"{cid} [{s['risk']}]: {s['aggregate']}")


if __name__ == "__main__":
    main()