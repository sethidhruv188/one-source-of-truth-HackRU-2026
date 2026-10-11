import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Panel, Table, Spinner, Badge, Notice } from "../components/ui";

function Dataset({ d }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="panel overflow-hidden">
      <button onClick={() => setOpen(!open)}
              className="w-full flex items-center justify-between gap-4 px-5 py-4
                         hover:bg-ink-700/40 transition-colors text-left">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5">
            <span className="text-sm font-medium">{d.title}</span>
            <Badge tone="neutral">{d.system}</Badge>
          </div>
          <div className="text-xs text-mist-500 mt-1 truncate max-w-2xl">{d.description}</div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {d.stale && <Badge tone="bad">stale</Badge>}
          {d.open_issues > 0 && <Badge tone="warn">{d.open_issues} issues</Badge>}
          {d.restricted_columns > 0 && <Badge tone="accent">{d.restricted_columns} restricted</Badge>}
          <span className="text-xs text-mist-700 tabular-nums">{d.rows.toLocaleString()} rows</span>
          <span className={`text-mist-500 transition-transform ${open ? "rotate-90" : ""}`}>›</span>
        </div>
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-4 border-t border-line pt-4">
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-3 text-xs">
            {[["Identifier", d.id, true], ["Owner", d.owner], ["Standard", d.cdisc_domain],
              ["Last refreshed", `${d.age_hours}h ago`], ["Licence", d.licence],
              ["Retrieval", d.retrieval, true]].map(([k, v, mono]) => (
              <div key={k}>
                <div className="label mb-1">{k}</div>
                <div className={`text-mist-300 ${mono ? "mono" : ""} break-words`}>{v}</div>
              </div>
            ))}
          </div>
          <div>
            <div className="label mb-1">Provenance</div>
            <div className="text-xs text-mist-300 leading-relaxed">{d.provenance}</div>
          </div>
          <div>
            <div className="label mb-2">Columns</div>
            <Table dense maxHeight="20rem"
              columns={["column", "type", "complete", "distinct", "example", "access", "meaning"]}
              rows={d.columns.map((c) => ({
                column: c.name, type: c.type,
                complete: `${Math.round(c.completeness * 100)}%`,
                distinct: c.distinct,
                example: c.restricted ? "—" : c.example,
                access: c.restricted ? "restricted" : "readable",
                meaning: c.description,
              }))} />
          </div>
        </div>
      )}
    </div>
  );
}

export default function Catalog() {
  const [q, setQ] = useState("");
  const [data, setData] = useState(null);
  const [map, setMap] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    const t = setTimeout(() => api.catalog(q).then(setData).catch((e) => setErr(e.message)), 180);
    return () => clearTimeout(t);
  }, [q]);

  if (err) return <Notice tone="bad" title="Request failed">{err}</Notice>;
  if (!data) return <Spinner label="Loading catalog" />;

  const met = data.fair.filter((f) => f.met).length;

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between gap-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Catalog</h1>
          <p className="text-sm text-mist-500 mt-1 max-w-3xl leading-relaxed">
            Metadata stays visible where the data is restricted. A role can see that a
            dataset exists and who owns it without being able to read it.
          </p>
        </div>
        <Badge tone="good">FAIR {met}/{data.fair.length}</Badge>
      </header>

      <input className="input" value={q} onChange={(e) => setQ(e.target.value)}
             placeholder="Search datasets, systems or columns" />

      <div className="space-y-3">
        {data.datasets.map((d) => <Dataset key={d.id} d={d} />)}
      </div>

      <Panel title="FAIR self-assessment" subtitle={data.standards.fair}>
        <Table dense maxHeight="24rem"
          columns={["principle", "requirement", "met", "how"]}
          rows={data.fair.map((f) => ({
            principle: f.principle, requirement: f.requirement,
            met: f.met ? "yes" : "no", how: f.evidence,
          }))} />
      </Panel>

      <Panel title="Identity mapping"
             subtitle={data.standards.harmonisation}
             right={<button className="btn-ghost text-[12px] py-1.5"
                            onClick={() => map ? setMap(null) : api.conceptMap().then(setMap)}>
                      {map ? "Hide" : "Show concept map"}
                    </button>}>
        {map
          ? <Table rows={map} dense maxHeight="22rem" />
          : <p className="text-xs text-mist-700">
              Every source identifier and the canonical concept it resolves to, in the
              shape an OMOP practitioner expects.
            </p>}
      </Panel>
    </div>
  );
}
