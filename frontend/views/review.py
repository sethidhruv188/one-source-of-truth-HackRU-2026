"""Review queue — the human half of identity matching."""

import streamlit as st

from backend.core import repository as repo, services as svc
from frontend import layout


def render(role_name):
    s = svc.matching_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("Identifiers seen", s["total"])
    c2.metric("Auto-matched", f"{s['auto']} ({s['auto_pct']:.0%})")
    c3.metric("Needs a human", s["pending"])

    st.caption("High-confidence matches resolve automatically. Ambiguous ones stop "
               "here, because a wrong site merge silently corrupts every downstream "
               "number. Decisions are recorded and survive a rebuild.")

    pending = svc.review_queue()
    if pending.empty:
        st.success("Nothing waiting for review.")

    for r in pending.itertuples():
        with st.container(border=True):
            a, b, c = st.columns([3, 3, 2])
            a.markdown(f"**{r.system} says**\n\n`{r.source_value}`")
            b.markdown(f"**Best match in CTMS**\n\n`{r.matched_against}`  \n"
                       f"site {r.canonical_site}")
            c.markdown(f"**Confidence**\n\n{r.confidence}")
            st.caption("Same country and same principal investigator; the difference "
                       "is an abbreviation.")
            x, y, _ = st.columns([1, 1, 4])
            if x.button("Confirm match", key=f"ok{r.Index}", type="primary"):
                with st.spinner("Recording and rebuilding..."):
                    svc.decide(r.system, r.source_value, r.canonical_site,
                               "confirm", role_name)
                st.rerun()
            if y.button("Not the same", key=f"no{r.Index}"):
                with st.spinner("Recording and rebuilding..."):
                    svc.decide(r.system, r.source_value, r.canonical_site,
                               "reject", role_name)
                st.rerun()

    log = repo.decisions()
    if len(log):
        with st.expander(f"Decision log  ·  {len(log)}"):
            layout.table(log)
            st.caption("Persisted. The system never asks the same question twice.")

    with st.expander("Full crosswalk"):
        layout.table(repo.crosswalk())
