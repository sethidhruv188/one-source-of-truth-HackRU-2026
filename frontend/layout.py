"""
layout.py — the parts of the UI that stay the same for every role.

Sidebar, header, theme, and the shared table/metric helpers live here. Views
import from this so the chrome is written once. What *changes* per role is
decided by the backend (which views exist, which questions, which columns);
this module only renders what it's handed.
"""

import streamlit as st

from backend.core import roles as roles_mod, services as svc

VIEW_LABELS = {
    "ask": "Ask",
    "graph": "Graph",
    "review": "Review queue",
    "catalog": "Catalog",
    "health": "Data health",
    "about": "How it works",
}

CSS = """
<style>
  .block-container {padding-top: 2.2rem; max-width: 1400px;}
  [data-testid="stMetricValue"] {font-size: 1.6rem;}
  .role-chip {display:inline-block; padding:2px 10px; border-radius:999px;
              background:#1e3a8a; color:#dbeafe; font-size:0.75rem;
              letter-spacing:.02em;}
  .withheld {border-left:3px solid #f59e0b; padding:.5rem .8rem;
             background:rgba(245,158,11,.08); font-size:.85rem; margin:.4rem 0;}
  .src {font-family: ui-monospace, monospace; font-size:.8rem; color:#94a3b8;}
</style>
"""


def page_setup():
    st.set_page_config(page_title="One Source of Truth",
                       page_icon="🔗", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)


def sidebar() -> str:
    """Identical for every role. Returns the selected role name."""
    with st.sidebar:
        st.markdown("### 🔗 One Source of Truth")
        st.caption("Cross-system answers for a clinical trial")
        st.markdown("---")

        role_name = st.selectbox("Signed in as", roles_mod.names())
        st.caption(svc.role_info(role_name).description)

        st.markdown("---")
        st.markdown("**Feed freshness**")
        for r in svc.feed_freshness().itertuples():
            icon = "🔴" if r.stale else ("🟡" if r.age_hours >= 24 else "🟢")
            age = f"{r.age_hours // 24}d" if r.age_hours >= 24 else f"{r.age_hours}h"
            st.caption(f"{icon} {r.system} — {age} ago")

        st.markdown("---")
        s = svc.matching_stats()
        st.markdown("**Identity matching**")
        st.caption(f"{s['auto_pct']:.0%} auto-matched · {s['pending']} awaiting review")

    return role_name


def header(role_name: str):
    c1, c2 = st.columns([4, 1])
    c1.title("One Source of Truth")
    c1.caption("One trial. Five systems. No shared IDs.")
    c2.markdown(f"<div style='text-align:right;padding-top:2rem'>"
                f"<span class='role-chip'>{role_name}</span></div>",
                unsafe_allow_html=True)


def withheld_notice(columns, role_name):
    if columns:
        st.markdown(
            f"<div class='withheld'>🔒 <b>{len(columns)} field(s) withheld</b> from "
            f"{role_name}: <code>{', '.join(columns)}</code><br>"
            f"Filtered in the service layer — this data was never sent to the browser."
            f"</div>", unsafe_allow_html=True)


def table(df, **kw):
    st.dataframe(df, use_container_width=True, hide_index=True, **kw)
