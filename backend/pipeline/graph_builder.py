"""
graph.py — build the knowledge graph.

Node types:
    Site      one real hospital (canonical)
    Patient   one real person
    Record    ONE ROW from ONE SOURCE FILE  <-- this is what makes lineage work
    Alias     an identifier a system uses for a site ("S701", "Mercy Gen. Hosp.")

Edge types:
    derived_from   Site/Patient  -> Record    (where this entity's data came from)
    alias_of       Alias         -> Site      (this system calls the site that)
    enrolled_at    Patient       -> Site
    reported_for   Record        -> Patient   (a safety case / AE about a patient)

Lineage is then just: walk the derived_from edges out of a node.

Run:  python src/graph.py
"""

import os
import pickle

import networkx as nx
import pandas as pd

from backend.core import config

OUT = str(config.PROCESSED)
GRAPH_PATH = str(config.GRAPH)


def build():
    G = nx.MultiDiGraph()

    master = pd.read_csv(f"{OUT}/site_master.csv")
    master["site_id"] = master["site_id"].astype(str)
    crosswalk = pd.read_csv(f"{OUT}/crosswalk.csv", dtype=str)

    # --- Site nodes --------------------------------------------------------
    for r in master.itertuples():
        G.add_node(f"site:{r.site_id}", kind="Site", label=r.site_name,
                   site_id=r.site_id,
                   enrolled_patients=int(r.enrolled_patients),
                   open_safety_cases=int(r.open_safety_cases),
                   kits_remaining=int(r.kits_remaining),
                   days_payment_overdue=int(r.days_payment_overdue),
                   systems_contributing=int(r.systems_contributing))

    # --- Alias nodes: every identifier any system uses for a site ----------
    for r in crosswalk.itertuples():
        if not r.canonical_site or pd.isna(r.canonical_site):
            continue
        alias = f"alias:{r.system}:{r.source_value}"
        G.add_node(alias, kind="Alias", label=r.source_value, system=r.system,
                   confidence=r.confidence, method=r.method, status=r.status)
        site = f"site:{r.canonical_site}"
        if site in G:
            G.add_edge(alias, site, kind="alias_of",
                       confidence=r.confidence, method=r.method)

    # --- Record nodes: one per source row, plus derived_from edges ---------
    feeds = {
        "edc_patients": ("patient_id", "Patient"),
        "edc_adverse_events": ("patient_id", "Event"),
        "ctms_sites": ("site_name", "SiteInfo"),
        "irt_supply": ("site", "Supply"),
        "safety_cases": ("case_patient_ref", "SafetyCase"),
        "finance_payments": ("hospital", "Payment"),
    }

    for feed, (idcol, record_kind) in feeds.items():
        df = pd.read_csv(f"{OUT}/resolved_{feed}.csv")
        for r in df.itertuples():
            rec = f"rec:{feed}:{r.source_row}"
            G.add_node(rec, kind="Record", record_kind=record_kind,
                       label=f"{feed} row {r.source_row}",
                       source_file=r.source_file, source_row=int(r.source_row),
                       value=str(getattr(r, idcol)))

            site = getattr(r, "canonical_site", None)
            if pd.notna(site) and f"site:{str(site)}" in G:
                G.add_edge(f"site:{str(site)}", rec, kind="derived_from")

            # Patients get their own nodes, and link to their site
            if feed == "edc_patients":
                p = f"patient:{r.patient_id}"
                G.add_node(p, kind="Patient", label=str(r.patient_id))
                G.add_edge(p, rec, kind="derived_from")
                if pd.notna(site):
                    G.add_edge(p, f"site:{str(site)}", kind="enrolled_at")

            if feed in ("safety_cases", "edc_adverse_events"):
                pid = getattr(r, "patient_id", None)
                if pd.notna(pid) and f"patient:{pid}" in G:
                    G.add_edge(rec, f"patient:{pid}", kind="reported_for")

    return G


# ----------------------------------------------------------------------------
# Queries over the graph
# ----------------------------------------------------------------------------

def lineage(G, node):
    """Every source row that contributed to this node."""
    rows = []
    for _, target, data in G.out_edges(node, data=True):
        if data.get("kind") == "derived_from":
            n = G.nodes[target]
            rows.append({"system": n["record_kind"],
                         "source_file": n["source_file"],
                         "source_row": n["source_row"],
                         "value": n["value"]})
    return pd.DataFrame(rows).sort_values(["source_file", "source_row"]) \
        if rows else pd.DataFrame()


def aliases(G, site_node):
    """Every identifier any system uses for this site."""
    rows = []
    for source, _, data in G.in_edges(site_node, data=True):
        if data.get("kind") == "alias_of":
            n = G.nodes[source]
            rows.append({"system": n["system"], "identifier": n["label"],
                         "confidence": n["confidence"], "method": n["method"]})
    return pd.DataFrame(rows)


def neighbourhood(G, site_node, max_records=12):
    """A small subgraph around one site, for drawing."""
    keep = {site_node}
    for source, _, d in G.in_edges(site_node, data=True):
        if d.get("kind") == "alias_of":
            keep.add(source)
    recs = [t for _, t, d in G.out_edges(site_node, data=True)
            if d.get("kind") == "derived_from"]
    keep.update(recs[:max_records])
    return G.subgraph(keep).copy()


def main():
    G = build()
    os.makedirs(OUT, exist_ok=True)
    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(G, f)

    kinds = pd.Series([d["kind"] for _, d in G.nodes(data=True)]).value_counts()
    edges = pd.Series([d.get("kind") for _, _, d in G.edges(data=True)]).value_counts()

    print("\nKnowledge graph built")
    print(f"  nodes  {G.number_of_nodes():>7}")
    print(f"  edges  {G.number_of_edges():>7}\n")
    print("  by node type")
    for k, v in kinds.items():
        print(f"    {k:<10} {v:>6}")
    print("\n  by edge type")
    for k, v in edges.items():
        print(f"    {k:<14} {v:>6}")

    demo = "site:701"
    if demo in G:
        print(f"\n  example — {G.nodes[demo]['label']} (site 701)")
        print("    known by:", ", ".join(
            f"{r.system}={r.identifier}" for r in aliases(G, demo).itertuples()))
        print(f"    built from {len(lineage(G, demo))} source rows")
    print(f"\n  saved to {GRAPH_PATH}")


if __name__ == "__main__":
    main()
