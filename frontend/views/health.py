"""Data health — quality issues scored against the planted answer key."""

import streamlit as st

from backend.core import services as svc
from frontend import layout


def render(role_name):
    rep = svc.quality_report(role_name)

    c1, c2, c3 = st.columns(3)
    c1.metric("Issues detected", rep["detected"])
    c2.metric("Planted defects caught", f"{rep['caught']}/{rep['planted']}")
    c3.metric("High severity", rep["high"])

    st.caption("The feeds are deliberately corrupted before loading, and the answer "
               "key is committed to the repo. This screen scores the pipeline "
               "against it.")

    layout.withheld_notice(rep["withheld_columns"], role_name)

    issues = rep["issues"]
    for t in issues["type"].unique():
        sub = issues[issues["type"] == t]
        with st.expander(f"{t.replace('_', ' ').title()}  ·  {len(sub)}"):
            layout.table(sub)

    st.markdown("#### Feed freshness")
    layout.table(svc.feed_freshness())
