"""Graph — the knowledge graph, inspected one site at a time."""

import streamlit as st

from backend.core import repository as repo, services as svc
from frontend import layout


def render(role_name):
    stats = svc.graph_stats()
    cols = st.columns(len(stats["by_kind"]) + 2)
    cols[0].metric("Nodes", f"{stats['nodes']:,}")
    cols[1].metric("Edges", f"{stats['edges']:,}")
    for i, (kind, n) in enumerate(stats["by_kind"].items()):
        cols[i + 2].metric(kind, f"{n:,}")

    st.caption("Every source row is a node. Entities point back to the rows they "
               "were built from, so lineage is a one-hop walk rather than a "
               "separate system.")

    G = repo.load_graph()
    sites = sorted([n for n, d in G.nodes(data=True) if d["kind"] == "Site"],
                   key=lambda n: G.nodes[n]["site_id"])
    pick = st.selectbox("Inspect a site", sites,
                        format_func=lambda n: f"{G.nodes[n]['site_id']} — "
                                              f"{G.nodes[n]['label']}")
    site_id = G.nodes[pick]["site_id"]

    st.markdown("**One hospital, four identifiers:**")
    layout.table(svc.site_aliases(site_id))

    lin = svc.lineage(site_id, role_name)
    st.markdown(f"**Built from {len(lin)} source rows**")
    layout.table(lin.head(100))

    with st.expander("Draw the neighbourhood"):
        try:
            import streamlit.components.v1 as components
            from pyvis.network import Network

            from backend.pipeline import graph_builder as kg

            sub = kg.neighbourhood(G, pick)
            net = Network(height="460px", width="100%", bgcolor="#0f172a",
                          font_color="#e2e8f0", directed=True)
            style = {"Site": ("#3b82f6", 34), "Alias": ("#f59e0b", 18),
                     "Record": ("#64748b", 8), "Patient": ("#10b981", 11)}
            for n, d in sub.nodes(data=True):
                colour, size = style.get(d["kind"], ("#999", 10))
                net.add_node(n, label=d.get("label", "")[:24], color=colour,
                             size=size, title=f"{d['kind']}: {d.get('label','')}")
            for a, b, d in sub.edges(data=True):
                net.add_edge(a, b, title=d.get("kind", ""))
            net.write_html("graph_view.html", notebook=False)
            components.html(open("graph_view.html").read(), height=480)
        except Exception as e:
            st.info(f"Graph drawing unavailable: {e}")
