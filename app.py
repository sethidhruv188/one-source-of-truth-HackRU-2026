"""
One Source of Truth — entry point.

Run from the project root:   streamlit run app.py

This file does one job: pick the views this role is allowed to see and render
them. All logic lives in backend/. All shared chrome lives in frontend/layout.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from backend.core import repository as repo, services as svc
from frontend import layout
from frontend.views import about, ask, catalog, graph, health, review

VIEWS = {"ask": ask, "graph": graph, "catalog": catalog,
         "review": review, "health": health, "about": about}

layout.page_setup()

if not repo.ready():
    st.error("No harmonised data yet. From the project root, run:\n\n"
             "```\npython3 -m backend.pipeline.build_data --synthetic\n"
             "python3 -m backend.pipeline.harmonize\n"
             "python3 -m backend.pipeline.graph_builder\n```")
    st.stop()

role_name = layout.sidebar()
layout.header(role_name)

allowed = svc.navigation(role_name)
tabs = st.tabs([layout.VIEW_LABELS[v] for v in allowed])
for tab, view_key in zip(tabs, allowed):
    with tab:
        VIEWS[view_key].render(role_name)
