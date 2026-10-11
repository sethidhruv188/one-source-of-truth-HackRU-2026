"""
repository.py — data access. The ONLY module that touches the database directory.

Nothing above this layer knows whether the store is CSV files, DuckDB, or Postgres.
Swapping the backing store means rewriting this file and nothing else.

Access is read-only except for `append_decision`, which records a human's
identity-match decision.
"""

import json
import pickle
from functools import lru_cache

import pandas as pd

from . import config


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _read(path_str, dtype=None):
    return pd.read_csv(path_str, dtype=dtype)


def clear_cache():
    """Call after any write so the next read sees fresh data."""
    _read.cache_clear()
    load_graph.cache_clear()


def site_master() -> pd.DataFrame:
    df = _read(str(config.PROCESSED / "site_master.csv")).copy()
    df["site_id"] = df["site_id"].astype(str)
    return df


def crosswalk() -> pd.DataFrame:
    return _read(str(config.PROCESSED / "crosswalk.csv"), dtype=str).copy()


def quality_issues() -> pd.DataFrame:
    return _read(str(config.PROCESSED / "quality_issues.csv")).copy()


def feed_metadata() -> pd.DataFrame:
    return _read(str(config.RAW / "_feed_metadata.csv")).copy()


def resolved(feed: str) -> pd.DataFrame:
    """A source feed with canonical_site and lineage columns attached."""
    return _read(str(config.PROCESSED / f"resolved_{feed}.csv")).copy()


def answer_key() -> dict:
    with open(config.ANSWER_KEY) as f:
        return json.load(f)


def decisions() -> pd.DataFrame:
    if config.CONFIRMED.exists():
        return pd.read_csv(config.CONFIRMED, dtype=str)
    return pd.DataFrame(columns=["system", "source_value", "canonical_site",
                                 "decided_by", "decided_at", "decision"])


@lru_cache(maxsize=1)
def load_graph():
    with open(config.GRAPH, "rb") as f:
        return pickle.load(f)


def ready() -> bool:
    return (config.PROCESSED / "site_master.csv").exists()


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

def append_decision(system, source_value, canonical_site, decision, decided_by):
    row = pd.DataFrame([{
        "system": system,
        "source_value": source_value,
        "canonical_site": canonical_site if decision == "confirm" else "",
        "decided_by": decided_by,
        "decided_at": pd.Timestamp.now().isoformat(timespec="seconds"),
        "decision": decision,
    }])
    out = pd.concat([decisions(), row], ignore_index=True)
    out.to_csv(config.CONFIRMED, index=False)
    clear_cache()
    return out


def catalog() -> dict:
    with open(config.PROCESSED / "catalog.json") as f:
        return json.load(f)
