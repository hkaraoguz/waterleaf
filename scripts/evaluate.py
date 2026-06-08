from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from pathlib import Path

from waterleaf.evaluation import score_predictions
from waterleaf.runtime import build_application


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Waterleaf plant identification.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--out", type=Path, default=Path("evaluation/results.json"))
    args = parser.parse_args()

    application = build_application()
    rows = []
    latencies = []
    with args.manifest.open(newline="") as handle:
        for item in csv.DictReader(handle):
            images = [Path(value) for value in item["images"].split("|") if value]
            started = time.perf_counter()
            result = application.identification.identify(images)
            latency = time.perf_counter() - started
            latencies.append(latency)
            rows.append(
                {
                    "case_id": item["case_id"],
                    "expected": item["expected_scientific_name"],
                    "predictions": [
                        candidate.scientific_name for candidate in result.candidates
                    ],
                    "latency_seconds": round(latency, 3),
                }
            )

    report = {
        "metrics": score_predictions(rows),
        "latency_seconds": {
            "mean": statistics.fmean(latencies) if latencies else 0,
            "median": statistics.median(latencies) if latencies else 0,
            "max": max(latencies, default=0),
        },
        "cases": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report["metrics"], indent=2))


if __name__ == "__main__":
    main()

