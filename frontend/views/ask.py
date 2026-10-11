"""Ask — preset cross-system questions, plus free-text questions via Gemini."""

import streamlit as st

from backend.core import services as svc
from frontend import layout

SUGGESTIONS = [
    "Which sites are running out of drug?",
    "Which sites have safety issues but haven't been paid?",
    "Average patients per site by country",
    "Top 5 sites by adverse events per patient",
    "Which sites are missing data from a system?",
]


# ---------------------------------------------------------------------------
# Shared lineage block — used by both modes
# ---------------------------------------------------------------------------

def _lineage_block(site_ids, role_name, key):
    if not site_ids:
        return
    st.markdown("#### Where did this come from?")
    site = st.selectbox("Trace a site back to its source rows", site_ids, key=key)

    st.markdown("**This site is known by:**")
    layout.table(svc.site_aliases(site))

    lin = svc.lineage(site, role_name)
    if len(lin):
        st.markdown(f"**Assembled from {len(lin)} source rows across "
                    f"{lin['system'].nunique()} systems**")
        layout.table(lin)
    else:
        st.info("No source records visible to this role.")


def _site_ids(df):
    """Pull site ids out of any result set that happens to have them."""
    if df is None or "site_id" not in df.columns:
        return []
    return df["site_id"].astype(str).tolist()


# ---------------------------------------------------------------------------
# Preset questions
# ---------------------------------------------------------------------------

def _preset(role_name):
    questions = svc.available_questions(role_name)
    if not questions:
        st.info("No questions are available to this role.")
        return

    keys = list(questions)
    default = svc.role_info(role_name).landing_question
    key = st.selectbox("Question", keys,
                       index=keys.index(default) if default in keys else 0,
                       format_func=lambda k: questions[k]["label"])
    res = svc.ask(key, role_name)

    c1, c2, c3 = st.columns(3)
    c1.metric("Sites matching", res["matched"])
    c2.metric("Systems joined", len(res["systems"]))
    c3.metric("Answer time", "< 1s")

    layout.withheld_notice(res["withheld_columns"], role_name)
    layout.table(res["rows"])

    with st.expander("The query that produced this"):
        st.code(res["sql"], language="sql")
        st.caption("Numbers come from the database, never from a language model.")

    _lineage_block(res["site_ids"], role_name, key="trace_preset")


# ---------------------------------------------------------------------------
# Free-text questions
# ---------------------------------------------------------------------------

def _freeform(role_name):
    if not svc.nl_available():
        st.info("Free-text questions need a Gemini API key. Put `GEMINI_API_KEY` in "
                "a `.env` file in the project root and reload. The preset questions "
                "work without it.")
        with st.expander("What this adds"):
            st.markdown(
                "Gemini writes the **query**. DuckDB returns the **numbers**. "
                "Gemini then writes one sentence *around* those numbers.\n\n"
                "A figure that passed through a language model is a figure you "
                "can't defend in a regulated setting, so the model never produces "
                "a value — only the SQL that fetches one.")
        return

    st.caption("Ask in plain English. The generated SQL is always shown, and the "
               "numbers come from the database, never from the model.")

    cols = st.columns(len(SUGGESTIONS))
    for i, s in enumerate(SUGGESTIONS):
        label = s if len(s) <= 24 else s[:22] + "…"
        if cols[i].button(label, key=f"sug{i}", use_container_width=True):
            st.session_state["nlq"] = s

    question = st.text_input("Your question",
                             value=st.session_state.get("nlq", ""),
                             placeholder="e.g. which sites enrolled well but are "
                                         "low on drug?")
    if not question:
        return

    with st.spinner("Writing the query…"):
        res = svc.ask_freeform(question, role_name)

    if res.get("sql"):
        with st.expander("Generated SQL", expanded=bool(res.get("error"))):
            st.code(res["sql"], language="sql")

    if res.get("error"):
        st.warning(res["error"])
        st.caption("The system says it can't answer rather than guessing. In a "
                   "regulated setting a confident wrong number is worse than no "
                   "number.")
        return

    if res.get("note"):
        st.info(res["note"])
        return

    df = res["rows"]
    c1, c2 = st.columns([1, 3])
    c1.metric("Rows returned", len(df))
    if res.get("explanation"):
        c2.info(res["explanation"])

    layout.withheld_notice(res.get("withheld_columns", []), role_name)
    layout.table(df)

    _lineage_block(_site_ids(df), role_name, key="trace_nl")


# ---------------------------------------------------------------------------

def render(role_name):
    mode = st.radio("mode", ["Ask anything", "Preset questions"],
                    horizontal=True, label_visibility="collapsed")
    st.markdown("")
    if mode == "Ask anything":
        _freeform(role_name)
    else:
        _preset(role_name)