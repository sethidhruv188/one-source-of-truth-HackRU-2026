"""
services.py — the middle layer.

Every request from the frontend passes through here, and every function takes a
`role`. Role filtering happens on the way out of this module, so a denied column
never reaches the presentation layer at all.

The frontend calls these. The frontend never calls repository directly.
"""

import subprocess
import sys

import pandas as pd

from . import config, repository as repo, roles as roles_mod


# ---------------------------------------------------------------------------
# Access control — applied to every DataFrame leaving this module
# ---------------------------------------------------------------------------

def _enforce(df: pd.DataFrame, role_name: str):
    """Drop denied columns. Returns (filtered_df, names_of_dropped_columns)."""
    role = roles_mod.get(role_name)
    dropped = [c for c in role.denied_columns if c in df.columns]
    return df.drop(columns=dropped), dropped


def navigation(role_name: str) -> tuple:
    return roles_mod.get(role_name).views


def role_info(role_name: str):
    return roles_mod.get(role_name)


# ---------------------------------------------------------------------------
# Questions — each one joins several systems
# ---------------------------------------------------------------------------

QUESTIONS = {
    "sites_at_risk": {
        "label": "Which sites have an open safety case AND low drug supply "
                 "AND overdue payments?",
        "systems": ["Safety", "IRT", "Finance", "CTMS"],
        "requires": ["open_safety_cases", "kits_remaining", "days_payment_overdue"],
        "sql": ("SELECT site_id, site_name, open_safety_cases, kits_remaining,\n"
                "       days_payment_overdue\n"
                "FROM site_master\n"
                "WHERE open_safety_cases > 0\n"
                "  AND kits_remaining < 15\n"
                "  AND days_payment_overdue > 30"),
        "fn": lambda d: d[(d.open_safety_cases > 0) & (d.kits_remaining < 15)
                          & (d.days_payment_overdue > 30)],
    },
    "low_supply": {
        "label": "Which sites are about to run out of study drug?",
        "systems": ["IRT", "CTMS", "EDC"],
        "requires": ["kits_remaining"],
        "sql": ("SELECT site_id, site_name, kits_remaining, enrolled_patients\n"
                "FROM site_master WHERE kits_remaining < 10\n"
                "ORDER BY kits_remaining"),
        "fn": lambda d: d[d.kits_remaining < 10].sort_values("kits_remaining"),
    },
    "under_enrolled": {
        "label": "Which sites are under their enrollment target?",
        "systems": ["EDC", "CTMS"],
        "requires": ["enrolled_patients"],
        "sql": ("SELECT site_id, site_name, enrolled_patients, enrollment_target\n"
                "FROM site_master WHERE enrolled_patients < enrollment_target"),
        "fn": lambda d: d[d.enrolled_patients < d.enrollment_target],
    },
    "incomplete_sites": {
        "label": "Which sites are missing data from one or more systems?",
        "systems": ["all"],
        "requires": ["systems_contributing"],
        "sql": ("SELECT site_id, site_name, systems_contributing\n"
                "FROM site_master WHERE systems_contributing < 5"),
        "fn": lambda d: d[d.systems_contributing < 5],
    },
    "overdue_payments": {
        "label": "Which sites have overdue payments, and how much is outstanding?",
        "systems": ["Finance", "CTMS"],
        "requires": ["days_payment_overdue", "invoice_amount_usd"],
        "sql": ("SELECT site_id, site_name, invoice_amount_usd, days_payment_overdue\n"
                "FROM site_master WHERE days_payment_overdue > 0\n"
                "ORDER BY days_payment_overdue DESC"),
        "fn": lambda d: d[d.days_payment_overdue > 0]
                         .sort_values("days_payment_overdue", ascending=False),
    },
    "safety_burden": {
        "label": "Which sites have the highest safety burden per patient?",
        "systems": ["Safety", "EDC"],
        "requires": ["open_safety_cases", "enrolled_patients"],
        "sql": ("SELECT site_id, site_name, open_safety_cases, enrolled_patients,\n"
                "       open_safety_cases * 1.0 / enrolled_patients AS per_patient\n"
                "FROM site_master WHERE enrolled_patients > 0\n"
                "ORDER BY per_patient DESC LIMIT 5"),
        "fn": lambda d: (d[d.enrolled_patients > 0]
                         .assign(per_patient=lambda x: (x.open_safety_cases
                                                        / x.enrolled_patients).round(3))
                         .nlargest(5, "per_patient")),
    },
}


def available_questions(role_name: str) -> dict:
    """
    A question is offered only if the role can see the columns it depends on.
    A Finance Analyst is not shown a safety question and then handed an empty
    table; the question simply isn't theirs to ask.
    """
    denied = set(roles_mod.get(role_name).denied_columns)
    return {k: q for k, q in QUESTIONS.items()
            if not denied.intersection(q["requires"])}


def ask(question_key: str, role_name: str) -> dict:
    q = QUESTIONS[question_key]
    result = q["fn"](repo.site_master())
    shown, dropped = _enforce(result, role_name)
    return {
        "label": q["label"],
        "sql": q["sql"],
        "systems": q["systems"],
        "rows": shown,
        "site_ids": result["site_id"].tolist(),
        "matched": len(result),
        "withheld_columns": dropped,
    }


# ---------------------------------------------------------------------------
# Lineage
# ---------------------------------------------------------------------------

FEED_SYSTEMS = [("EDC", "edc_patients", "patient_id"),
                ("Safety", "safety_cases", "case_patient_ref"),
                ("IRT", "irt_supply", "site"),
                ("Finance", "finance_payments", "hospital"),
                ("CTMS", "ctms_sites", "site_name")]


def lineage(site_id: str, role_name: str) -> pd.DataFrame:
    """Source rows behind a site, restricted to systems this role may see."""
    denied = set(roles_mod.get(role_name).denied_columns)
    rows = []
    for system, feed, idcol in FEED_SYSTEMS:
        if system == "EDC" and "enrolled_patients" in denied:
            continue           # Finance cannot trace into patient-level records
        if system == "Safety" and "open_safety_cases" in denied:
            continue
        if system == "Finance" and "invoice_amount_usd" in denied:
            continue
        df = repo.resolved(feed)
        sub = df[df["canonical_site"].astype(str) == str(site_id)]
        for r in sub.head(60).itertuples():
            rows.append({"system": system, "source_file": r.source_file,
                         "source_row": r.source_row, "record": getattr(r, idcol)})
    return pd.DataFrame(rows)


def site_aliases(site_id: str) -> pd.DataFrame:
    cw = repo.crosswalk()
    return (cw[cw.canonical_site == str(site_id)]
            [["system", "source_value", "confidence", "method", "status"]]
            .rename(columns={"source_value": "identifier"}))


# ---------------------------------------------------------------------------
# Identity matching
# ---------------------------------------------------------------------------

def matching_stats() -> dict:
    cw = repo.crosswalk()
    auto = cw.status.isin(["auto_matched", "human_confirmed"]).sum()
    return {"total": len(cw), "auto": int(auto),
            "auto_pct": auto / len(cw) if len(cw) else 0,
            "pending": int((cw.status == "needs_review").sum()),
            "no_match": int((cw.status == "no_match").sum())}


def review_queue() -> pd.DataFrame:
    cw = repo.crosswalk()
    return cw[cw.status == "needs_review"]


def decide(system, source_value, canonical_site, decision, decided_by):
    """Record a human decision, then rebuild so it propagates everywhere."""
    repo.append_decision(system, source_value, canonical_site, decision, decided_by)
    rebuild()


def rebuild():
    for module in ("backend.pipeline.harmonize", "backend.pipeline.graph_builder"):
        subprocess.run([sys.executable, "-m", module],
                       cwd=config.ROOT, capture_output=True)
    repo.clear_cache()


# ---------------------------------------------------------------------------
# Data quality
# ---------------------------------------------------------------------------

def quality_report(role_name: str) -> dict:
    issues = repo.quality_issues()
    key = repo.answer_key()
    caught = sum(1 for d in key["defects"]
                 if d["type"] in set(issues["type"])) if len(issues) else 0
    shown, dropped = _enforce(issues, role_name)
    return {"issues": shown, "detected": len(issues),
            "planted": key["total_planted_defects"], "caught": caught,
            "high": int((issues.severity == "high").sum()) if len(issues) else 0,
            "withheld_columns": dropped}


def feed_freshness() -> pd.DataFrame:
    meta = repo.feed_metadata().copy()
    now = pd.Timestamp("2026-10-11 09:00")
    meta["age_hours"] = ((now - pd.to_datetime(meta.loaded_at))
                         .dt.total_seconds() / 3600).round(0).astype(int)
    meta["stale"] = meta.age_hours >= 72
    return meta[["system", "feed", "age_hours", "stale"]]


def graph_stats() -> dict:
    G = repo.load_graph()
    kinds = pd.Series([d["kind"] for _, d in G.nodes(data=True)]).value_counts()
    return {"nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
            "by_kind": kinds.to_dict()}


# ---------------------------------------------------------------------------
# Catalog (FAIR)
# ---------------------------------------------------------------------------

def catalog(role_name: str, search: str = "") -> dict:
    """
    Dataset metadata. FAIR principle A2: metadata stays visible even where the
    underlying columns are denied — a role can learn that a dataset exists and
    who owns it without being able to read it.
    """
    cat = repo.catalog()
    denied = set(roles_mod.get(role_name).denied_columns)
    entries = []
    for e in cat["datasets"]:
        cols = []
        for c in e["columns"]:
            c = dict(c)
            c["restricted"] = c["name"] in denied
            cols.append(c)
        entry = dict(e)
        entry["columns"] = cols
        entry["restricted_columns"] = sum(1 for c in cols if c["restricted"])
        entry["readable"] = entry["restricted_columns"] < len(cols)
        entries.append(entry)

    if search:
        s = search.lower()
        entries = [e for e in entries
                   if s in e["title"].lower() or s in e["description"].lower()
                   or s in e["system"].lower()
                   or any(s in c["name"].lower() for c in e["columns"])]

    return {"datasets": entries, "fair": cat["fair_assessment"],
            "standards": cat["standards"], "generated_at": cat["generated_at"]}


def source_to_concept_map() -> pd.DataFrame:
    """
    The crosswalk, presented in the OHDSI source_to_concept_map shape
    (The Book of OHDSI, ch. 6): every source identifier, the concept it resolves
    to, and how that mapping was established.
    """
    cw = repo.crosswalk()
    return pd.DataFrame({
        "source_code": cw.source_value,
        "source_vocabulary_id": cw.system,
        "target_concept_id": cw.canonical_site,
        "target_vocabulary_id": "OST_SITE",
        "mapping_method": cw.method,
        "confidence": cw.confidence,
        "status": cw.status,
    })

def ask_freeform(question: str, role_name: str) -> dict:
    """Natural-language question. Role filtering still applies on the way out."""
    from . import nl_query
    res = nl_query.ask(question, role_name)
    if "rows" in res and res["rows"] is not None:
        res["rows"], res["withheld_columns"] = _enforce(res["rows"], role_name)
    return res


def nl_available() -> bool:
    from . import nl_query
    return nl_query.available()
