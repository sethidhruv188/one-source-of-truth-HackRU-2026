"""
run_pipeline.py — one command to go from nothing to a ready app.

    python3 run_pipeline.py              real CDISC data if present, public APIs if reachable
    python3 run_pipeline.py --synthetic  no downloads, no network
    python3 run_pipeline.py --offline    use CDISC if present, skip the APIs
"""

import subprocess
import sys

STEPS = [
    ("Fetching public reference data", "backend.pipeline.fetch_public", "network"),
    ("Building source feeds", "backend.pipeline.build_data", None),
    ("Harmonising identities", "backend.pipeline.harmonize", None),
    ("Building knowledge graph", "backend.pipeline.graph_builder", None),
    ("Cataloguing datasets", "backend.pipeline.catalog_builder", None),
]


def main():
    synthetic = "--synthetic" in sys.argv
    offline = synthetic or "--offline" in sys.argv

    for i, (title, module, needs) in enumerate(STEPS, 1):
        if needs == "network" and offline:
            print(f"[{i}/{len(STEPS)}] {title} — skipped")
            continue
        print(f"\n[{i}/{len(STEPS)}] {title}")
        args = [sys.executable, "-m", module]
        if module.endswith("build_data") and synthetic:
            args.append("--synthetic")
        r = subprocess.run(args)
        if r.returncode != 0:
            sys.exit(f"\nFailed at: {title}")

    print("\nReady.  streamlit run app.py")


if __name__ == "__main__":
    main()
