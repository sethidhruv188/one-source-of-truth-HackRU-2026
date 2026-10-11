"""How it works."""

import streamlit as st


def render(role_name):
    st.markdown("""
#### The problem
A trial's data lives in separate systems — EDC, CTMS, drug supply, safety, finance —
and none of them use the same IDs. The same hospital is `SITE-0701` in one, `701` in
another, `S701` in a third, and `Mercy General Hospital` in a fourth. One cross-system
question takes weeks of spreadsheet reconciliation, and the answer isn't traceable.

#### Architecture

```
frontend/   Streamlit views. Renders only. Never reads the database.
   │  calls
backend/core/services.py    business logic + ACCESS CONTROL
   │  calls
backend/core/repository.py  the only module that touches stored data
   │
database/   raw feeds, harmonised output, the graph
```

Role filtering happens in the service layer, on the way out. A column a role may
not see is never sent to the browser, so there is nothing for the UI to hide.

#### Pipeline
1. **Ingest** five feeds, stamping every row with its source file and row number.
2. **Harmonise** IDs: deterministic where possible, fuzzy name matching where not,
   human review where the match isn't confident.
3. **Graph**: sites, patients, aliases and one node per source row.
4. **Check quality** against a planted answer key.
5. **Answer** cross-system questions, with lineage on every number.

#### Data
The EDC feed is the real
[CDISC SDTM/ADaM pilot study](https://github.com/cdisc-org/sdtm-adam-pilot-project),
used with attribution to CDISC. The other four feeds are synthetic, derived from the
same sites so a correct answer exists and can be measured. No real person is
identifiable: the clinical data is de-identified and every name is generated.

Designed to the [FAIR principles](https://www.nature.com/articles/sdata201618).
""")
