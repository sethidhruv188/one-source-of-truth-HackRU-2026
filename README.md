# One Source of Truth

**One clinical trial. Five systems. No shared IDs.**

A trial's data lives in separate systems — EDC, CTMS, drug supply (IRT), safety and
finance — and none of them agree on identifiers. The same hospital is `SITE-0701` in
one, `701` in another, `S701` in a third, and `Mercy General Hospital` in a fourth.
A question like *"which sites have an open safety case AND low drug supply AND
overdue payments?"* takes weeks of manual spreadsheet reconciliation today, and the
answer still isn't traceable.

This answers it in under a second, and every number traces back to the source row it
came from.

Built for the Regeneron prize at HackRU 2026 (starter sheet 40).

---

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python3 run_pipeline.py          # or --synthetic for no network, no downloads
streamlit run app.py
```

Optional, for the real clinical data:

```bash
git clone --depth 1 https://github.com/cdisc-org/sdtm-adam-pilot-project.git database/cdisc
python3 run_pipeline.py
```

Every external dependency degrades gracefully. No CDISC clone, no network, no API
key — it still runs.

---

## Results

| | |
|---|---|
| Identifiers harmonised | **70** across 5 systems |
| Auto-matched | **96%** |
| Sent to human review | 3 ambiguous name variants |
| Planted data defects caught | **11 / 11** |
| Knowledge graph | ~1,500 nodes · ~2,700 edges |
| FAIR criteria met | **10 / 10** |

The feeds are deliberately corrupted before loading — duplicates, orphan records,
impossible dates, mangled facility names, a stale feed — and the answer key is
committed at `database/raw/answer_key.json`. The Data health screen scores itself
against it.

---

## Architecture

```
frontend/   Streamlit views. Renders only. Never reads the database.
   │  calls
backend/core/services.py     business logic + ACCESS CONTROL
   │  calls
backend/core/repository.py   the only module that touches stored data
   │
database/   raw feeds, harmonised output, graph, catalog
```

**Why the middle layer exists.** Role filtering happens in `services.py`, on the way
out. A column a role may not see is never sent to the browser, so there is nothing
for the UI to hide. Swapping CSV storage for Postgres means rewriting
`repository.py` and nothing else.

### Pipeline

```
run_pipeline.py
  1  fetch_public      ClinicalTrials.gov + openFDA (optional, graceful fallback)
  2  build_data        real study -> 5 disagreeing feeds + answer key
  3  harmonize         crosswalk, lineage, quality checks, wide table
  4  graph_builder     knowledge graph
  5  catalog_builder   FAIR metadata + column profiling
```

### Identity resolution

```
SITE-0701 (EDC) ─┐
701       (CTMS) ├─▶  canonical site 701
S701      (IRT) ─┤
"Mercy General Hosp." (Finance) ─┘  fuzzy, 0.90 — sent to a human
```

Deterministic matches resolve automatically. Anything under 95% confidence stops at
a review queue with both records side by side, because a wrong site merge silently
corrupts every downstream number. Confirmed decisions persist and survive a rebuild,
so the system never asks the same question twice.

### Lineage

Every row is stamped with `source_file` and `source_row` at ingest, and becomes a
`Record` node in the graph. Entities carry `derived_from` edges to the rows that
produced them, so tracing a number is a one-hop walk rather than a separate system.

---

## Roles

| Role | Tabs | Questions | Cannot see |
|---|---|---|---|
| Study Manager | 6 | 6 | — |
| Finance Analyst | 4 | 3 | patient and safety data |
| Site Monitor | 6 | 4 | financial data |
| Data Steward | 6 | 5 | patient detail, finance amounts |

Role changes four things: which tabs exist, which questions can be asked, which
columns come back, and how far lineage can be traced. Adding a role is one entry in
`backend/core/roles.py`.

---

## Standards

| Standard | How it's applied |
|---|---|
| [FAIR](https://www.nature.com/articles/sdata201618) (Wilkinson et al. 2016) | Persistent identifiers, column-level metadata, per-dataset licence and provenance, searchable catalog. Metadata stays visible where data is restricted (A2). Self-assessment in the Catalog view. |
| CDISC SDTM | EDC feeds map to SDTM domains (DM, AE) |
| [OHDSI / OMOP](https://ohdsi.github.io/TheBookOfOhdsi/) | Identity resolution follows the `source_to_concept_map` pattern; exposed in that shape in the Catalog view |

## Data sources

| Feed | Source |
|---|---|
| EDC patients, adverse events | **Real** — [CDISC SDTM/ADaM pilot](https://github.com/cdisc-org/sdtm-adam-pilot-project), study CDISCPILOT01 |
| CTMS facility names | **Real** — [ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/about-api) |
| AE terminology | **Real** — [openFDA FAERS](https://open.fda.gov/apis/drug/event/) MedDRA reaction terms |
| IRT, finance, operational fields | Synthetic, derived from the same sites so a correct answer exists and can be measured |

No individual is identifiable. The clinical data is de-identified and every person
name is generated.

Clinical data © CDISC, used with attribution under their terms and not redistributed
here — `build_data` reads it from your own clone.

## Layout

```
app.py                      entry point — routing only
run_pipeline.py             one command, five steps
backend/
  core/      config · roles · repository · services
  pipeline/  fetch_public · build_data · harmonize · graph_builder · catalog_builder
frontend/
  layout.py  sidebar, header, theme — identical for every role
  views/     ask · graph · catalog · review · health · about
database/
  raw/       the five messy feeds + answer key
  processed/ harmonised output, graph.pkl, catalog.json
```

## License

MIT. CDISC source data remains under CDISC's terms.
