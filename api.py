"""
api.py — HTTP layer for the React frontend.

Thin by design. Every endpoint delegates to backend.core.services, which is where
business logic and access control already live. This file only translates between
HTTP and Python: no filtering, no joins, no rules.

Run:  uvicorn api:app --reload --port 8000
Docs: http://localhost:8000/docs
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.core import repository as repo, roles as roles_mod, services as svc

app = FastAPI(title="One Source of Truth API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Auth — demo accounts, one per role
# ---------------------------------------------------------------------------

USERS = {
    "dhruv":  {"password": "demo", "name": "Dhruv Sethi",   "role": "Study Manager"},
    "fiona":  {"password": "demo", "name": "Fiona Reyes",   "role": "Finance Analyst"},
    "marcus": {"password": "demo", "name": "Marcus Oyelaran", "role": "Site Monitor"},
    "sana":   {"password": "demo", "name": "Sana Qureshi",  "role": "Data Steward"},
}


class Login(BaseModel):
    username: str
    password: str


def current_role(x_role: str = Header(None)) -> str:
    """
    The role for this request. A session token would carry this in production;
    for the demo the client sends it as a header after logging in.
    """
    if not x_role or x_role not in roles_mod.ROLES:
        raise HTTPException(401, "Unknown or missing role")
    return x_role


def records(df):
    """DataFrame -> JSON-safe list of dicts. NaN/NaT become null."""
    if df is None or len(df) == 0:
        return []
    return json.loads(df.to_json(orient="records", date_format="iso"))


# ---------------------------------------------------------------------------

@app.get("/api/health")
def healthcheck():
    return {"ok": True, "data_ready": repo.ready()}


@app.post("/api/login")
def login(body: Login):
    user = USERS.get(body.username.lower())
    if not user or user["password"] != body.password:
        raise HTTPException(401, "Invalid username or password")
    role = roles_mod.get(user["role"])
    return {"username": body.username.lower(), "name": user["name"],
            "role": role.name, "description": role.description,
            "views": list(role.views)}


@app.get("/api/me")
def me(role: str = Header(None, alias="X-Role")):
    r = roles_mod.get(current_role(role))
    return {"role": r.name, "description": r.description, "views": list(r.views),
            "denied_columns": list(r.denied_columns),
            "landing_question": r.landing_question}


@app.get("/api/roles")
def list_roles():
    return [{"name": r.name, "description": r.description, "views": list(r.views)}
            for r in roles_mod.ROLES.values()]


# --- dashboard -------------------------------------------------------------

@app.get("/api/kpis")
def kpis(role: str = Header(None, alias="X-Role")):
    r = current_role(role)
    master, _ = svc._enforce(repo.site_master(), r)
    stats = svc.matching_stats()
    quality = svc.quality_report(r)
    out = {"sites": len(master),
           "auto_matched_pct": round(stats["auto_pct"] * 100),
           "pending_review": stats["pending"],
           "defects_caught": quality["caught"],
           "defects_planted": quality["planted"]}
    for col, label in [("enrolled_patients", "patients"),
                       ("open_safety_cases", "open_safety_cases"),
                       ("kits_remaining", "kits_remaining"),
                       ("days_payment_overdue", "sites_overdue")]:
        if col in master.columns:
            out[label] = (int(master[col].sum()) if col != "days_payment_overdue"
                          else int((master[col] > 0).sum()))
    return out


@app.get("/api/sites")
def sites(role: str = Header(None, alias="X-Role")):
    rows, withheld = svc._enforce(repo.site_master(), current_role(role))
    return {"rows": records(rows), "withheld_columns": withheld}


# --- questions -------------------------------------------------------------

@app.get("/api/questions")
def questions(role: str = Header(None, alias="X-Role")):
    qs = svc.available_questions(current_role(role))
    return [{"key": k, "label": q["label"], "systems": q["systems"]}
            for k, q in qs.items()]


@app.get("/api/ask/{key}")
def ask(key: str, role: str = Header(None, alias="X-Role")):
    r = current_role(role)
    if key not in svc.available_questions(r):
        raise HTTPException(403, "That question is not available to this role")
    res = svc.ask(key, r)
    return {"label": res["label"], "sql": res["sql"], "systems": res["systems"],
            "matched": res["matched"], "rows": records(res["rows"]),
            "site_ids": res["site_ids"],
            "withheld_columns": res["withheld_columns"]}


class Question(BaseModel):
    question: str


@app.post("/api/ask")
def ask_freeform(body: Question, role: str = Header(None, alias="X-Role")):
    r = current_role(role)
    if not svc.nl_available():
        raise HTTPException(503, "GEMINI_API_KEY not configured")
    res = svc.ask_freeform(body.question, r)
    rows = res.get("rows")
    return {"sql": res.get("sql"), "error": res.get("error"),
            "note": res.get("note"), "explanation": res.get("explanation"),
            "rows": records(rows),
            "site_ids": (rows["site_id"].astype(str).tolist()
                         if rows is not None and "site_id" in getattr(rows, "columns", [])
                         else []),
            "withheld_columns": res.get("withheld_columns", [])}


@app.get("/api/nl-available")
def nl_available():
    return {"available": svc.nl_available()}


# --- lineage ---------------------------------------------------------------

@app.get("/api/lineage/{site_id}")
def lineage(site_id: str, role: str = Header(None, alias="X-Role")):
    r = current_role(role)
    return {"site_id": site_id,
            "aliases": records(svc.site_aliases(site_id)),
            "sources": records(svc.lineage(site_id, r))}


# --- catalog ---------------------------------------------------------------

@app.get("/api/catalog")
def catalog(q: str = "", role: str = Header(None, alias="X-Role")):
    return svc.catalog(current_role(role), q)


@app.get("/api/concept-map")
def concept_map():
    return records(svc.source_to_concept_map())


# --- review queue ----------------------------------------------------------

@app.get("/api/review")
def review(role: str = Header(None, alias="X-Role")):
    current_role(role)
    return {"stats": svc.matching_stats(),
            "pending": records(svc.review_queue()),
            "decisions": records(repo.decisions())}


class Decision(BaseModel):
    system: str
    source_value: str
    canonical_site: str
    decision: str          # "confirm" | "reject"


@app.post("/api/review/decide")
def decide(body: Decision, role: str = Header(None, alias="X-Role")):
    r = current_role(role)
    if body.decision not in ("confirm", "reject"):
        raise HTTPException(400, "decision must be 'confirm' or 'reject'")
    svc.decide(body.system, body.source_value, body.canonical_site,
               body.decision, r)
    return {"ok": True, "stats": svc.matching_stats(),
            "pending": records(svc.review_queue())}


# --- data quality ----------------------------------------------------------

@app.get("/api/quality")
def quality(role: str = Header(None, alias="X-Role")):
    rep = svc.quality_report(current_role(role))
    return {"detected": rep["detected"], "planted": rep["planted"],
            "caught": rep["caught"], "high": rep["high"],
            "issues": records(rep["issues"]),
            "withheld_columns": rep["withheld_columns"],
            "feeds": records(svc.feed_freshness())}


# --- graph -----------------------------------------------------------------

@app.get("/api/graph/stats")
def graph_stats():
    return svc.graph_stats()


@app.get("/api/graph/site/{site_id}")
def graph_site(site_id: str, limit: int = 60):
    """Node/link JSON for a force-directed view of one site."""
    G = repo.load_graph()
    node_id = f"site:{site_id}"
    if node_id not in G:
        raise HTTPException(404, "No such site")

    keep = {node_id}
    keep |= {s for s, _, d in G.in_edges(node_id, data=True)
             if d.get("kind") == "alias_of"}
    patients = [s for s, _, d in G.in_edges(node_id, data=True)
                if d.get("kind") == "enrolled_at"]
    keep |= set(patients[:limit // 3])
    recs = [t for _, t, d in G.out_edges(node_id, data=True)
            if d.get("kind") == "derived_from"]
    keep |= set(recs[:limit])
    for p in patients[:limit // 3]:
        keep |= {t for _, t, d in G.out_edges(p, data=True)
                 if d.get("kind") == "derived_from"}

    sub = G.subgraph(keep)
    nodes = [{"id": n, "kind": d["kind"], "label": d.get("label", ""),
              "source_file": d.get("source_file"), "source_row": d.get("source_row"),
              "system": d.get("system"), "confidence": d.get("confidence")}
             for n, d in sub.nodes(data=True)]
    links = [{"source": a, "target": b, "kind": d.get("kind", "")}
             for a, b, d in sub.edges(data=True)]
    return {"nodes": nodes, "links": links}
