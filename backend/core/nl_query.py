"""
nl_query.py — natural language to SQL, over the harmonised table only.

Gemini writes the query. DuckDB runs it. Numbers come from the database and never
pass through the model. The schema shown to the model is already role-filtered, so
the model cannot write a query against a column this role may not see.
"""

import os
import re

import duckdb
import google.generativeai as genai
from dotenv import load_dotenv

from . import repository as repo, roles as roles_mod

load_dotenv()
_key = os.getenv("GEMINI_API_KEY")
if _key:
    genai.configure(api_key=_key)

MODEL = "gemini-3.8-flash"          
FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|copy)\b", re.I)

COLUMN_MEANINGS = {
    "site_id": "canonical site identifier (string)",
    "site_name": "hospital name",
    "principal_investigator": "lead doctor at the site",
    "country": "site country",
    "enrollment_target": "patients the site agreed to enrol",
    "enrolled_patients": "patients actually enrolled",
    "open_safety_cases": "unresolved serious adverse event cases",
    "adverse_events": "total adverse events reported",
    "kits_remaining": "study drug kits on hand (low = supply risk)",
    "kits_shipped": "study drug kits shipped to the site",
    "invoice_amount_usd": "total invoiced to the site",
    "days_payment_overdue": "days past the payment due date",
    "systems_contributing": "how many of the 5 systems hold data for this site",
}

EXAMPLES = """
Q: which sites are running out of drug?
A: SELECT site_id, site_name, kits_remaining FROM site_master WHERE kits_remaining < 10 ORDER BY kits_remaining

Q: top 5 sites by enrolment
A: SELECT site_id, site_name, enrolled_patients FROM site_master ORDER BY enrolled_patients DESC LIMIT 5

Q: sites with safety issues that also owe us money
A: SELECT site_id, site_name, open_safety_cases, days_payment_overdue FROM site_master WHERE open_safety_cases > 0 AND days_payment_overdue > 0

Q: average kits left per country
A: SELECT country, ROUND(AVG(kits_remaining),1) AS avg_kits FROM site_master GROUP BY country
"""


def available() -> bool:
    return bool(_key)


def _schema(role_name: str) -> str:
    denied = set(roles_mod.get(role_name).denied_columns)
    cols = [c for c in repo.site_master().columns if c not in denied]
    return "\n".join(f"  {c} — {COLUMN_MEANINGS.get(c, '')}" for c in cols)


def _prompt(question: str, role_name: str) -> str:
    return f"""You write DuckDB SQL for one table called site_master.

Columns available to this user:
{_schema(role_name)}

Rules:
- Output ONLY the SQL. No markdown fences, no explanation.
- SELECT statements only.
- Use ONLY the columns listed above. If the question needs a column that is not
  listed, output exactly: UNANSWERABLE
- Always include site_id and site_name unless the query aggregates them away.

Examples:
{EXAMPLES}

Q: {question}
A:"""


def to_sql(question: str, role_name: str) -> str:
    model = genai.GenerativeModel(MODEL)
    sql = model.generate_content(_prompt(question, role_name)).text.strip()
    sql = re.sub(r"^```(?:sql)?|```$", "", sql, flags=re.M).strip()
    return sql


def run(sql: str, role_name: str):
    """Execute, with the role's denied columns absent from the table entirely."""
    denied = set(roles_mod.get(role_name).denied_columns)
    df = repo.site_master().drop(columns=[c for c in denied
                                          if c in repo.site_master().columns])
    con = duckdb.connect()
    con.register("site_master", df)
    try:
        return con.execute(sql).df()
    finally:
        con.close()


def explain(question: str, rows) -> str:
    """One sentence of context. Never restates or recomputes the numbers."""
    model = genai.GenerativeModel(MODEL)
    preview = rows.head(10).to_string(index=False)
    return model.generate_content(
        f"""A clinical trial manager asked: "{question}"
The database returned {len(rows)} row(s):
{preview}

Write ONE sentence explaining what this means operationally. Do not restate the
numbers, do not invent any figure that is not above, do not add a greeting."""
    ).text.strip()


def ask(question: str, role_name: str) -> dict:
    """Returns sql, rows, explanation, error — whichever applies."""
    if not available():
        return {"error": "GEMINI_API_KEY not set in .env"}
    try:
        sql = to_sql(question, role_name)
    except Exception as e:
        return {"error": f"Model unavailable: {e}"}

    if sql.upper().startswith("UNANSWERABLE"):
        return {"sql": None,
                "error": "That needs data this role isn't permitted to see, or a "
                         "column that doesn't exist."}
    if FORBIDDEN.search(sql) or not sql.lower().lstrip().startswith("select"):
        return {"sql": sql, "error": "Only SELECT queries are allowed."}

    try:
        rows = run(sql, role_name)
    except Exception as e:
        return {"sql": sql, "error": f"Query failed: {e}"}

    if rows.empty:
        return {"sql": sql, "rows": rows, "explanation": None,
                "note": "No sites matched."}
    try:
        note = explain(question, rows)
    except Exception:
        note = None
    return {"sql": sql, "rows": rows, "explanation": note}