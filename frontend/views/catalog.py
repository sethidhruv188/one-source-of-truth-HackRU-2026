"""Catalog — FAIR metadata for every dataset, plus the OHDSI-style concept map."""

import streamlit as st

from backend.core import services as svc
from frontend import layout


def render(role_name):
    search = st.text_input("Search datasets, systems or columns",
                           placeholder="e.g. safety, kits, site_id")
    cat = svc.catalog(role_name, search)

    met = sum(1 for f in cat["fair"] if f["met"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Datasets", len(cat["datasets"]))
    c2.metric("Columns", sum(d["column_count"] for d in cat["datasets"]))
    c3.metric("Rows", f"{sum(d['rows'] for d in cat['datasets']):,}")
    c4.metric("FAIR criteria met", f"{met}/{len(cat['fair'])}")

    st.caption("Metadata stays visible even where the data is restricted — FAIR "
               "principle A2. A role can see that a dataset exists and who owns it "
               "without being able to read it.")

    for d in cat["datasets"]:
        flags = []
        if d["stale"]:
            flags.append("🔴 stale")
        if d["open_issues"]:
            flags.append(f"⚠️ {d['open_issues']} issue(s)")
        if d["restricted_columns"]:
            flags.append(f"🔒 {d['restricted_columns']} restricted")
        suffix = "  ·  " + "  ".join(flags) if flags else ""

        with st.expander(f"**{d['title']}**  ·  {d['system']}  ·  "
                         f"{d['rows']:,} rows{suffix}"):
            st.markdown(d["description"])

            a, b = st.columns(2)
            a.markdown(f"**Identifier**  \n`{d['id']}`")
            a.markdown(f"**Owner**  \n{d['owner']}")
            a.markdown(f"**Standard**  \n{d['cdisc_domain']}")
            b.markdown(f"**Last refreshed**  \n{d['age_hours']}h ago")
            b.markdown(f"**Licence**  \n{d['licence']}")
            b.markdown(f"**Retrieval**  \n`{d['retrieval']}`")

            st.markdown(f"**Provenance**  \n{d['provenance']}")

            if d["issue_types"]:
                st.warning("Known issues: " + ", ".join(
                    t.replace("_", " ") for t in d["issue_types"]))

            st.markdown("**Columns**")
            rows = [{"column": c["name"],
                     "type": c["type"],
                     "complete": f"{c['completeness']:.0%}",
                     "distinct": c["distinct"],
                     "example": "—" if c["restricted"] else c["example"],
                     "access": "🔒 restricted" if c["restricted"] else "readable",
                     "meaning": c["description"]}
                    for c in d["columns"]]
            layout.table(rows)

    st.markdown("---")
    st.markdown("#### FAIR self-assessment")
    st.caption(f"Against {cat['standards']['fair']}")
    layout.table([{"principle": f["principle"],
                   "requirement": f["requirement"],
                   "met": "✅" if f["met"] else "—",
                   "how": f["evidence"]} for f in cat["fair"]])

    with st.expander("Identity mapping in OHDSI source_to_concept_map form"):
        st.caption(cat["standards"]["harmonisation"])
        layout.table(svc.source_to_concept_map())
