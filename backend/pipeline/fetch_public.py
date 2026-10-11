"""
fetch_public.py — pull the two public APIs the starter sheet names.

  ClinicalTrials.gov API v2  -> real facility names for the CTMS site master
  openFDA drug event (FAERS) -> real MedDRA reaction terms for adverse events

Both are optional. If a fetch fails or is skipped, build_data falls back to
generated values, so the pipeline never breaks because an API was down.

Run:  python3 -m backend.pipeline.fetch_public
      python3 -m backend.pipeline.fetch_public --inspect   (dump raw JSON shape)
"""

import json
import sys
import urllib.request

import pandas as pd

from backend.core import config

CTGOV = ("https://clinicaltrials.gov/api/v2/studies"
         "?query.cond=alzheimer%20disease"
         "&filter.overallStatus=RECRUITING"
         "&pageSize=50")

FAERS = ("https://api.fda.gov/drug/event.json"
         "?count=patient.reaction.reactionmeddrapt.exact&limit=80")


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "one-source-of-truth/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def fetch_sites(inspect=False):
    """Real hospital names. These are messy in exactly the way we need."""
    try:
        data = _get(CTGOV)
    except Exception as e:
        print(f"  ClinicalTrials.gov unavailable ({e}) — will use generated names")
        return None

    studies = data.get("studies", [])
    if inspect and studies:
        print(json.dumps(studies[0], indent=1)[:1200])

    rows = []
    for s in studies:
        p = s.get("protocolSection", {})
        nct = p.get("identificationModule", {}).get("nctId")
        for loc in p.get("contactsLocationsModule", {}).get("locations", []):
            if loc.get("facility"):
                rows.append({"nct_id": nct, "facility": loc["facility"],
                             "city": loc.get("city"), "state": loc.get("state"),
                             "country": loc.get("country", "USA")})

    if not rows:
        print("  ClinicalTrials.gov returned no locations — using generated names")
        return None

    df = (pd.DataFrame(rows).drop_duplicates("facility")
                            .sort_values("facility").reset_index(drop=True))
    df.to_csv(config.RAW / "_ctgov_sites.csv", index=False)
    print(f"  ClinicalTrials.gov: {len(df)} real facilities "
          f"from {df.nct_id.nunique()} studies")
    return df


def fetch_reactions(inspect=False):
    """Real MedDRA preferred terms, weighted by real-world reporting frequency."""
    try:
        data = _get(FAERS)
    except Exception as e:
        print(f"  openFDA unavailable ({e}) — will use a default term list")
        return None

    results = data.get("results", [])
    if inspect and results:
        print(json.dumps(results[:3], indent=1))
    if not results:
        return None

    df = pd.DataFrame(results).rename(columns={"term": "reaction",
                                               "count": "frequency"})
    df.to_csv(config.RAW / "_faers_reactions.csv", index=False)
    print(f"  openFDA FAERS: {len(df)} real reaction terms "
          f"(top: {df.reaction.iloc[0]})")
    return df


def main():
    inspect = "--inspect" in sys.argv
    print("Fetching public reference data...")
    fetch_sites(inspect)
    fetch_reactions(inspect)
    print("\nRun build_data next; it picks these up automatically if present.")


if __name__ == "__main__":
    main()
