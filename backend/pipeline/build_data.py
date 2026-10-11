"""
build_data.py — turn the real CDISC pilot study into five DISAGREEING system feeds.

Simulates what a real trial looks like: EDC, CTMS, IRT (drug supply), Safety and
Finance, each using its own site IDs, its own date formats, and its own spelling
of the same hospital. Also plants a known set of data-quality defects and writes
an answer key so we can measure how many we catch.

Usage:
    python scripts/build_data.py                 # uses data/cdisc if present
    python scripts/build_data.py --synthetic     # no CDISC clone needed
"""

import argparse
import json
import os
import random
from datetime import datetime, timedelta

import pandas as pd

random.seed(42)

from backend.core import config

SDTM = str(config.SDTM)
RAW = str(config.RAW)

# Fake hospital names, one per site. Finance refers to sites ONLY by name,
# which is what forces the fuzzy-matching step.
HOSPITALS = [
    "Mercy General Hospital", "St. Vincent Medical Center", "Riverside Clinical Research",
    "Northgate University Hospital", "Lakeview Medical Group", "Pinecrest Health System",
    "Fairmont Regional Hospital", "Oakhill Neurology Institute", "Summit Care Center",
    "Bayside Memorial Hospital", "Westbrook Medical Center", "Clearwater Health Partners",
    "Highland Park Hospital", "Cedar Grove Research Clinic", "Kingsway General Hospital",
    "Brookfield Medical Institute", "Stonebridge Health Center", "Ashford Regional Medical",
    "Glenwood Clinical Center", "Thornton Memorial Hospital",
]


# ----------------------------------------------------------------------------
# 1. Load the real study (or fall back to synthetic)
# ----------------------------------------------------------------------------

def real_hospital_names():
    """Real facility names from ClinicalTrials.gov, if fetch_public has run."""
    f = config.RAW / "_ctgov_sites.csv"
    if f.exists():
        names = pd.read_csv(f)["facility"].dropna().tolist()
        if names:
            print(f"Using {len(names)} real facility names from ClinicalTrials.gov")
            return names
    return HOSPITALS


def real_reaction_terms():
    """Real MedDRA terms from openFDA FAERS, if fetch_public has run."""
    f = config.RAW / "_faers_reactions.csv"
    if f.exists():
        df = pd.read_csv(f)
        if len(df):
            print(f"Using {len(df)} real reaction terms from openFDA")
            return df["reaction"].tolist(), df["frequency"].tolist()
    return (["HEADACHE", "DIZZINESS", "NAUSEA", "RASH", "FATIGUE"], None)


def load_cdisc():
    """Read the real CDISC pilot SDTM datasets. Returns (patients, adverse_events)."""
    dm = pd.read_sas(f"{SDTM}/dm.xpt", encoding="utf-8")
    ae = pd.read_sas(f"{SDTM}/ae.xpt", encoding="utf-8")

    patients = dm[["USUBJID", "SITEID", "AGE", "SEX", "ARM", "COUNTRY",
                   "RFSTDTC", "RFENDTC"]].copy()
    patients.columns = ["patient_id", "site_num", "age", "sex", "arm",
                        "country", "enroll_date", "end_date"]

    events = ae[["USUBJID", "AETERM", "AESEV", "AESER", "AESTDTC"]].copy()
    events.columns = ["patient_id", "event_term", "severity", "serious", "event_date"]
    return patients, events


def make_synthetic():
    """Fallback if the CDISC clone isn't available. Same shape, invented data."""
    rows, events = [], []
    for s in range(701, 718):
        for i in range(random.randint(12, 25)):
            pid = f"01-{s}-{1000 + i}"
            start = datetime(2026, 1, 1) + timedelta(days=random.randint(0, 120))
            rows.append({
                "patient_id": pid, "site_num": str(s),
                "age": random.randint(55, 85),
                "sex": random.choice(["M", "F"]),
                "arm": random.choice(["Placebo", "Low Dose", "High Dose"]),
                "country": "USA",
                "enroll_date": start.strftime("%Y-%m-%d"),
                "end_date": (start + timedelta(days=180)).strftime("%Y-%m-%d"),
            })
            for _ in range(random.randint(0, 4)):
                events.append({
                    "patient_id": pid,
                    "event_term": random.choice(
                        ["HEADACHE", "DIZZINESS", "NAUSEA", "RASH", "FATIGUE"]),
                    "severity": random.choice(["MILD", "MODERATE", "SEVERE"]),
                    "serious": random.choice(["N", "N", "N", "Y"]),
                    "event_date": (start + timedelta(days=random.randint(1, 150))
                                   ).strftime("%Y-%m-%d"),
                })
    return pd.DataFrame(rows), pd.DataFrame(events)


# ----------------------------------------------------------------------------
# 2. Fan the one real source out into five systems that disagree
# ----------------------------------------------------------------------------

def build_feeds(patients, events, defects):
    sites = sorted(patients["site_num"].unique())
    pool = real_hospital_names()
    names = {s: pool[i % len(pool)] for i, s in enumerate(sites)}

    # --- EDC: site is "SITE-0701", dates ISO -------------------------------
    edc = patients.copy()
    edc["site_id"] = "SITE-0" + edc["site_num"].astype(str)
    edc = edc[["patient_id", "site_id", "age", "sex", "arm", "country",
               "enroll_date", "end_date"]]

    # DEFECT: three impossible dates (enrollment after study end)
    bad_dates = edc.sample(3, random_state=1).index
    for idx in bad_dates:
        edc.loc[idx, "enroll_date"] = "2027-12-31"
        defects.append({"type": "impossible_date", "feed": "edc_patients.csv",
                        "key": edc.loc[idx, "patient_id"],
                        "detail": "enrollment date after study end date"})

    # --- CTMS: site is bare number, dates DD/MM/YYYY -----------------------
    ctms = pd.DataFrame({
        "site_code": [int(s) for s in sites],
        "site_name": [names[s] for s in sites],
        "principal_investigator": [f"Dr. {n.split()[0]}" for n in
                                   (names[s] for s in sites)],
        "country": "USA",
        "activation_date": [(datetime(2025, 6, 1) + timedelta(days=random.randint(0, 200))
                             ).strftime("%d/%m/%Y") for _ in sites],
        "enrollment_target": [random.randint(15, 40) for _ in sites],
    })

    # DEFECT: two duplicated site rows
    dupes = ctms.sample(2, random_state=2)
    ctms = pd.concat([ctms, dupes], ignore_index=True)
    for _, r in dupes.iterrows():
        defects.append({"type": "duplicate_record", "feed": "ctms_sites.csv",
                        "key": str(r["site_code"]),
                        "detail": "site appears twice in CTMS export"})

    # --- IRT (drug supply): site is "S701", dates DDMMMYYYY ----------------
    irt_rows = []
    for s in sites:
        shipped = random.randint(40, 120)
        used = random.randint(20, shipped)
        irt_rows.append({
            "site": f"S{s}",
            "kits_shipped": shipped,
            "kits_used": used,
            "kits_remaining": shipped - used,
            "last_shipment": (datetime(2026, 9, 1) + timedelta(days=random.randint(0, 35))
                              ).strftime("%d%b%Y").upper(),
        })
    irt = pd.DataFrame(irt_rows)

    # Guarantee a few genuinely low-supply sites so the demo question has answers
    for idx in irt.sample(3, random_state=3).index:
        irt.loc[idx, "kits_remaining"] = random.randint(0, 4)

    # DEFECT: two orphan sites that exist in no other system
    orphans = pd.DataFrame([
        {"site": "S799", "kits_shipped": 30, "kits_used": 10, "kits_remaining": 20,
         "last_shipment": "15SEP2026"},
        {"site": "S801", "kits_shipped": 25, "kits_used": 25, "kits_remaining": 0,
         "last_shipment": "02OCT2026"},
    ])
    irt = pd.concat([irt, orphans], ignore_index=True)
    for o in ["S799", "S801"]:
        defects.append({"type": "orphan_record", "feed": "irt_supply.csv", "key": o,
                        "detail": "site exists in IRT but in no other system"})

    # --- Safety: patient IDs prefixed, NO site column at all ---------------
    serious = events[events["serious"] == "Y"].copy()
    if len(serious) < 20:
        serious = events.sample(min(40, len(events)), random_state=4).copy()
    safety = pd.DataFrame({
        "case_patient_ref": "PT_" + serious["patient_id"].astype(str),
        "case_term": serious["event_term"],
        "severity": serious["severity"],
        "case_status": [random.choice(["OPEN", "OPEN", "CLOSED"]) for _ in range(len(serious))],
        "reported_date": serious["event_date"],
    })

    # --- Finance: site referenced ONLY by name, some names misspelled ------
    fin_rows = []
    for s in sites:
        fin_rows.append({
            "hospital": names[s],
            "invoice_amount_usd": round(random.uniform(20000, 180000), 2),
            "invoice_date": (datetime(2026, 7, 1) + timedelta(days=random.randint(0, 60))
                             ).strftime("%m-%d-%Y"),
            "days_payment_overdue": random.choice([0, 0, 0, 12, 28, 45, 67, 91]),
        })
    finance = pd.DataFrame(fin_rows)

        # DEFECT: three mangled facility names (forces fuzzy matching + human review).
    # Abbreviate common words and truncate, the way a legacy finance system with a
    # short name field would. Works for long international names as well as short ones.
    ABBREV = [("University", "Univ"), ("Hospital", "Hosp"), ("General", "Gen"),
              ("Medical", "Med"), ("Center", "Ctr"), ("Centre", "Ctr"),
              ("Institute", "Inst"), ("Regional", "Reg"), ("Clinical", "Clin"),
              ("Research", "Res"), ("Health", "Hlth"), ("Memorial", "Mem")]

    def mangle(name, limit=30):
        s = name
        for a, b in ABBREV:
            s = s.replace(a, b)
        return s.replace('"', "").strip()[:limit].strip()

    changed = 0
    for idx in finance.index:
        if changed >= 3:
            break
        original = finance.loc[idx, "hospital"]
        variant = mangle(original)
        if variant == original or len(variant) < 8:
            continue
        finance.loc[idx, "hospital"] = variant
        changed += 1
        defects.append({"type": "name_variant", "feed": "finance_payments.csv",
                        "key": variant,
                        "detail": f"same site as '{original}', written differently"})

    return edc, events, ctms, irt, safety, finance, names


# ----------------------------------------------------------------------------
# 3. Write everything out
# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true",
                    help="skip the CDISC clone and invent the base study")
    args = ap.parse_args()

    os.makedirs(RAW, exist_ok=True)

    if not args.synthetic and os.path.exists(f"{SDTM}/dm.xpt"):
        print("Reading real CDISC pilot study...")
        patients, events = load_cdisc()
        source = "CDISC SDTM/ADaM pilot project (study CDISCPILOT01)"
    else:
        print("CDISC data not found — generating synthetic base study.")
        patients, events = make_synthetic()
        source = "synthetic (CDISC structure)"

    defects = []
    edc, ae, ctms, irt, safety, finance, names = build_feeds(patients, events, defects)

    edc.to_csv(f"{RAW}/edc_patients.csv", index=False)
    ae.to_csv(f"{RAW}/edc_adverse_events.csv", index=False)
    ctms.to_csv(f"{RAW}/ctms_sites.csv", index=False)
    irt.to_csv(f"{RAW}/irt_supply.csv", index=False)
    safety.to_csv(f"{RAW}/safety_cases.csv", index=False)
    finance.to_csv(f"{RAW}/finance_payments.csv", index=False)

    # Feed metadata — drives the freshness / stale-feed check.
    # DEFECT: the finance feed is deliberately 9 days stale.
    now = datetime(2026, 10, 11, 9, 0)
    feeds = [
        {"feed": "edc_patients.csv", "system": "EDC", "loaded_at": now.isoformat()},
        {"feed": "edc_adverse_events.csv", "system": "EDC", "loaded_at": now.isoformat()},
        {"feed": "ctms_sites.csv", "system": "CTMS",
         "loaded_at": (now - timedelta(hours=6)).isoformat()},
        {"feed": "irt_supply.csv", "system": "IRT",
         "loaded_at": (now - timedelta(days=1)).isoformat()},
        {"feed": "safety_cases.csv", "system": "Safety",
         "loaded_at": (now - timedelta(hours=3)).isoformat()},
        {"feed": "finance_payments.csv", "system": "Finance",
         "loaded_at": (now - timedelta(days=9)).isoformat()},
    ]
    pd.DataFrame(feeds).to_csv(f"{RAW}/_feed_metadata.csv", index=False)
    defects.append({"type": "stale_feed", "feed": "finance_payments.csv",
                    "key": "finance_payments.csv",
                    "detail": "feed has not refreshed in 9 days"})

    with open(f"{RAW}/answer_key.json", "w") as f:
        json.dump({"base_data_source": source,
                   "total_planted_defects": len(defects),
                   "defects": defects}, f, indent=2)

    print(f"\nWrote 6 feeds to {RAW}/")
    print(f"  EDC patients      {len(edc):>6}")
    print(f"  EDC adverse events{len(ae):>6}")
    print(f"  CTMS sites        {len(ctms):>6}")
    print(f"  IRT supply        {len(irt):>6}")
    print(f"  Safety cases      {len(safety):>6}")
    print(f"  Finance payments  {len(finance):>6}")
    print(f"\nPlanted {len(defects)} defects (answer key: {RAW}/answer_key.json)")


if __name__ == "__main__":
    main()
