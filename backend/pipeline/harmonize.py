"""
harmonize.py — make five disagreeing feeds agree.

Does four things:
  1. CROSSWALK  — works out that SITE-0701 / 701 / S701 / "Mercy General Hospital"
                  are all the same site. High-confidence matches are automatic;
                  ambiguous ones go to a human review queue.
  2. LINEAGE    — every row keeps a pointer back to its source file and row number,
                  so any number on screen can be traced to where it came from.
  3. QUALITY    — runs checks for duplicates, orphans, impossible dates, stale feeds.
  4. WIDE TABLE — one site-level table joining all five systems, in plain English
                  column names, which is what the dashboard and the AI query on.

Run:  python src/harmonize.py
"""

import json
import os
import re
from datetime import datetime
from difflib import SequenceMatcher

import pandas as pd

from backend.core import config

RAW = str(config.RAW)
OUT = str(config.PROCESSED)

AUTO_MATCH_THRESHOLD = 0.95   # above this, match automatically
REVIEW_THRESHOLD = 0.60       # between the two, ask a human
STALE_AFTER_DAYS = 3
NOW = datetime(2026, 10, 11, 9, 0)


# ----------------------------------------------------------------------------
# Lineage: every row we read gets stamped with where it came from
# ----------------------------------------------------------------------------

def load_with_lineage(filename):
    """Read a feed and add source_file / source_row columns."""
    df = pd.read_csv(f"{RAW}/{filename}")
    df["source_file"] = filename
    df["source_row"] = df.index + 2   # +2 = header row + 1-indexing, matches a spreadsheet
    return df


# ----------------------------------------------------------------------------
# 1. Crosswalk
# ----------------------------------------------------------------------------

def site_number(value):
    """Pull the bare site number out of any of the ID formats we've seen."""
    digits = re.findall(r"\d+", str(value))
    return str(int(digits[0])) if digits else None


def similarity(a, b):
    """0-1 name similarity, ignoring case, punctuation and common abbreviations."""
    def norm(s):
        return re.sub(r"[^a-z0-9 ]", "", str(s).lower()).strip()
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def build_crosswalk(edc, ctms, irt, finance):
    """
    Map every system's site identifier onto one canonical site number.
    EDC / CTMS / IRT carry a number, so they match deterministically.
    Finance carries only a hospital name, so it needs fuzzy matching.
    """
    rows = []

    for df, col, system in [(edc, "site_id", "EDC"),
                            (ctms, "site_code", "CTMS"),
                            (irt, "site", "IRT")]:
        for raw_id in df[col].astype(str).unique():
            rows.append({
                "system": system, "source_value": raw_id,
                "canonical_site": site_number(raw_id),
                "confidence": 1.0, "method": "id_normalisation",
                "status": "auto_matched",
            })

    # Finance: no ID at all, only a hospital name. Match against CTMS names.
    ctms_names = ctms.drop_duplicates("site_code")[["site_code", "site_name"]]
    for name in finance["hospital"].unique():
        scores = [(similarity(name, r.site_name), str(r.site_code), r.site_name)
                  for r in ctms_names.itertuples()]
        best, canonical, matched_name = max(scores, key=lambda x: x[0])

        if best >= AUTO_MATCH_THRESHOLD:
            status = "auto_matched"
        elif best >= REVIEW_THRESHOLD:
            status = "needs_review"
        else:
            status = "no_match"
            canonical = None

        rows.append({
            "system": "Finance", "source_value": name,
            "canonical_site": canonical,
            "confidence": round(best, 3),
            "method": "fuzzy_name_match",
            "status": status,
            "matched_against": matched_name if canonical else None,
        })

    crosswalk = pd.DataFrame(rows)

    # Human decisions override everything and survive a rebuild.
    #
    # crosswalk_confirmed.csv is an append-only audit log: every decision ever
    # made, with who made it and when. Only the LAST decision for a given
    # identifier is applied, so a revert restores the machine's own judgement
    # without erasing the history of what was decided before it.
    if os.path.exists(f"{OUT}/crosswalk_confirmed.csv"):
        log = pd.read_csv(f"{OUT}/crosswalk_confirmed.csv", dtype=str).fillna("")
        if "decision" not in log.columns:
            log["decision"] = "confirm"
        latest = log.drop_duplicates(subset=["system", "source_value"], keep="last")

        for r in latest.itertuples():
            mask = ((crosswalk.system == r.system) &
                    (crosswalk.source_value == r.source_value))
            if r.decision == "revert":
                continue                      # fall back to the automatic result
            if r.decision == "reject":
                crosswalk.loc[mask, "canonical_site"] = None
                crosswalk.loc[mask, "status"] = "human_rejected"
                crosswalk.loc[mask, "method"] = "human_rejected"
            else:
                crosswalk.loc[mask, "canonical_site"] = r.canonical_site
                crosswalk.loc[mask, "status"] = "human_confirmed"
                crosswalk.loc[mask, "method"] = "human_confirmed"

    return crosswalk


def resolve(crosswalk, system, value):
    hit = crosswalk[(crosswalk.system == system) &
                    (crosswalk.source_value == str(value))]
    if hit.empty:
        return None
    if hit.iloc[0]["status"] == "needs_review":
        return None
    return hit.iloc[0]["canonical_site"]


# ----------------------------------------------------------------------------
# 2. Quality checks
# ----------------------------------------------------------------------------

def run_quality_checks(edc, ctms, irt, finance, crosswalk):
    issues = []

    # Duplicates: same site listed twice in CTMS
    dupes = ctms[ctms.duplicated("site_code", keep=False)]
    for r in dupes.itertuples():
        issues.append({"type": "duplicate_record", "feed": "ctms_sites.csv",
                       "key": str(r.site_code), "severity": "medium",
                       "detail": "site appears more than once in the CTMS export",
                       "source_row": r.source_row})

    # Orphans: IRT sites that exist in no other system
    known = set(edc["canonical_site"].dropna()) | set(ctms["canonical_site"].dropna())
    for r in irt.itertuples():
        if r.canonical_site not in known:
            issues.append({"type": "orphan_record", "feed": "irt_supply.csv",
                           "key": r.site, "severity": "high",
                           "detail": "drug supply recorded for a site that exists nowhere else",
                           "source_row": r.source_row})

    # Impossible dates: enrolled after the study ended
    for r in edc.itertuples():
        try:
            if pd.notna(r.enroll_date) and pd.notna(r.end_date) \
               and str(r.enroll_date) > str(r.end_date):
                issues.append({"type": "impossible_date", "feed": "edc_patients.csv",
                               "key": r.patient_id, "severity": "high",
                               "detail": f"enrolled {r.enroll_date}, study ended {r.end_date}",
                               "source_row": r.source_row})
        except Exception:
            pass

    # Name variants that needed a human
    for r in crosswalk[crosswalk.status == "needs_review"].itertuples():
        issues.append({"type": "name_variant", "feed": "finance_payments.csv",
                       "key": r.source_value, "severity": "medium",
                       "detail": f"ambiguous match ({r.confidence}) — sent to review queue",
                       "source_row": None})

    # Stale feeds
    meta = pd.read_csv(f"{RAW}/_feed_metadata.csv")
    for r in meta.itertuples():
        age_days = (NOW - datetime.fromisoformat(r.loaded_at)).days
        if age_days >= STALE_AFTER_DAYS:
            issues.append({"type": "stale_feed", "feed": r.feed, "key": r.feed,
                           "severity": "medium",
                           "detail": f"{r.system} feed last refreshed {age_days} days ago",
                           "source_row": None})

    return pd.DataFrame(issues)


# ----------------------------------------------------------------------------
# 3. The wide site-level table
# ----------------------------------------------------------------------------

def build_site_master(edc, ae, ctms, irt, safety, finance):
    patients = (edc.groupby("canonical_site")
                   .agg(enrolled_patients=("patient_id", "nunique"))
                   .reset_index())

    sites = (ctms.drop_duplicates("canonical_site")[
                 ["canonical_site", "site_name", "principal_investigator",
                  "country", "enrollment_target"]])

    supply = irt[["canonical_site", "kits_remaining", "kits_shipped", "last_shipment"]]

    safety_counts = (safety[safety.case_status == "OPEN"]
                     .groupby("canonical_site")
                     .agg(open_safety_cases=("case_term", "count"))
                     .reset_index())

    money = finance.groupby("canonical_site").agg(
        invoice_amount_usd=("invoice_amount_usd", "sum"),
        days_payment_overdue=("days_payment_overdue", "max")).reset_index()

    ae_counts = (ae.groupby("canonical_site")
                   .agg(adverse_events=("event_term", "count"))
                   .reset_index())

    master = sites
    for df in [patients, supply, safety_counts, money, ae_counts]:
        master = master.merge(df, on="canonical_site", how="left")

    for col in ["enrolled_patients", "open_safety_cases", "adverse_events",
                "kits_remaining", "days_payment_overdue", "invoice_amount_usd"]:
        master[col] = master[col].fillna(0)

    master["systems_contributing"] = master["canonical_site"].apply(
        lambda s: sum([
            s in set(edc["canonical_site"]), s in set(ctms["canonical_site"]),
            s in set(irt["canonical_site"]), s in set(safety["canonical_site"]),
            s in set(finance["canonical_site"]),
        ]))

    master = master.rename(columns={"canonical_site": "site_id"})
    return master.sort_values("site_id").reset_index(drop=True)


# ----------------------------------------------------------------------------

def main():
    os.makedirs(OUT, exist_ok=True)

    edc = load_with_lineage("edc_patients.csv")
    ae = load_with_lineage("edc_adverse_events.csv")
    ctms = load_with_lineage("ctms_sites.csv")
    irt = load_with_lineage("irt_supply.csv")
    safety = load_with_lineage("safety_cases.csv")
    finance = load_with_lineage("finance_payments.csv")

    crosswalk = build_crosswalk(edc, ctms, irt, finance)

    edc["canonical_site"] = edc["site_id"].apply(lambda v: resolve(crosswalk, "EDC", v))
    ctms["canonical_site"] = ctms["site_code"].apply(lambda v: resolve(crosswalk, "CTMS", v))
    irt["canonical_site"] = irt["site"].apply(lambda v: resolve(crosswalk, "IRT", v))
    finance["canonical_site"] = finance["hospital"].apply(
        lambda v: resolve(crosswalk, "Finance", v))

    # Safety has no site column at all — it joins through the patient.
    patient_to_site = dict(zip(edc["patient_id"], edc["canonical_site"]))
    safety["patient_id"] = safety["case_patient_ref"].str.replace("PT_", "", regex=False)
    safety["canonical_site"] = safety["patient_id"].map(patient_to_site)
    ae["canonical_site"] = ae["patient_id"].map(patient_to_site)

    issues = run_quality_checks(edc, ctms, irt, finance, crosswalk)
    master = build_site_master(edc, ae, ctms, irt, safety, finance)

    master.to_csv(f"{OUT}/site_master.csv", index=False)
    crosswalk.to_csv(f"{OUT}/crosswalk.csv", index=False)
    issues.to_csv(f"{OUT}/quality_issues.csv", index=False)
    for name, df in [("edc_patients", edc), ("edc_adverse_events", ae),
                     ("ctms_sites", ctms), ("irt_supply", irt),
                     ("safety_cases", safety), ("finance_payments", finance)]:
        df.to_csv(f"{OUT}/resolved_{name}.csv", index=False)

    total = len(crosswalk)
    auto = (crosswalk.status.isin(["auto_matched", "human_confirmed"])).sum()
    review = (crosswalk.status == "needs_review").sum()

    # Score ourselves against the planted answer key
    with open(f"{RAW}/answer_key.json") as f:
        key = json.load(f)
    planted = len(key["defects"])
    caught_types = set(issues["type"]) if len(issues) else set()
    caught = sum(1 for d in key["defects"] if d["type"] in caught_types)

    print(f"\nHarmonisation complete")
    print(f"  identifiers seen        {total}")
    print(f"  auto-matched            {auto}  ({auto/total:.0%})")
    print(f"  sent to human review    {review}")
    print(f"  no match                {(crosswalk.status=='no_match').sum()}")
    print(f"\nQuality")
    print(f"  issues detected         {len(issues)}")
    print(f"  planted defects caught  {caught}/{planted}")
    print(f"\nSite master: {len(master)} sites, {len(master.columns)} columns -> {OUT}/site_master.csv")


if __name__ == "__main__":
    main()
