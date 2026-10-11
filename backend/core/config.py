"""Every path in the project resolves from here, so scripts work from any cwd."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATABASE = ROOT / "database"
RAW = DATABASE / "raw"
PROCESSED = DATABASE / "processed"
CDISC = DATABASE / "cdisc"

SDTM = CDISC / "updated-pilot-submission-package/900172/m5/datasets/cdiscpilot01/tabulations/sdtm"

GRAPH = PROCESSED / "graph.pkl"
ANSWER_KEY = RAW / "answer_key.json"
CONFIRMED = PROCESSED / "crosswalk_confirmed.csv"

for d in (RAW, PROCESSED):
    d.mkdir(parents=True, exist_ok=True)
