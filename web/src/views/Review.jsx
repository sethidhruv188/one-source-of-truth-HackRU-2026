import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Panel, Stat, Table, Spinner, Badge, Notice, Empty } from "../components/ui";

export default function Review() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");

  const load = () => api.review().then(setData).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  async function decide(row, decision) {
    setBusy(row.source_value);
    setErr("");
    try {
      await api.decide({
        system: row.system,
        source_value: row.source_value,
        canonical_site: String(row.canonical_site ?? ""),
        decision,
      });
      await load();
    } catch (e) { setErr(e.message); }
    setBusy("");
  }

  async function revert(entry) {
    setBusy(entry.source_value);
    setErr("");
    try {
      await api.revert(entry.system, entry.source_value);
      await load();
    } catch (e) { setErr(e.message); }
    setBusy("");
  }

  if (err && !data) return <Notice tone="bad" title="Request failed">{err}</Notice>;
  if (!data) return <Spinner label="Loading review queue" />;

  const { stats, pending, decisions } = data;
  const applied = decisions.filter((d) => d.in_effect).length;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl font-semibold tracking-tight">Review queue</h1>
        <p className="text-sm text-mist-500 mt-1 max-w-3xl leading-relaxed">
          Deterministic matches resolve automatically. Anything below 95% confidence
          stops here, because a wrong site merge silently corrupts every downstream
          number.
        </p>
      </header>

      {err && <Notice tone="bad" title="Request failed">{err}</Notice>}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat label="Identifiers seen" value={stats.total} />
        <Stat label="Auto-matched" value={`${Math.round(stats.auto_pct * 100)}%`}
              hint={`${stats.auto} of ${stats.total}`} tone="good" />
        <Stat label="Awaiting a human" value={stats.pending}
              tone={stats.pending ? "warn" : "good"} />
        <Stat label="Decisions in effect" value={applied}
              hint={`${decisions.length} logged`} />
      </div>

      {pending.length === 0 ? (
        <Panel title="Queue clear"><Empty>Nothing is waiting for review.</Empty></Panel>
      ) : (
        <div className="space-y-3">
          {pending.map((r) => (
            <div key={r.source_value} className="panel p-5">
              <div className="grid lg:grid-cols-[1fr_1fr_auto_auto] gap-5 items-center">
                <div>
                  <div className="label mb-1.5">{r.system} records it as</div>
                  <div className="mono text-[15px] text-mist-100">{r.source_value}</div>
                </div>
                <div>
                  <div className="label mb-1.5">Closest match in CTMS</div>
                  <div className="mono text-[15px] text-mist-100">{r.matched_against}</div>
                  <div className="text-[11px] text-mist-700 mt-1">site {r.canonical_site}</div>
                </div>
                <div className="text-center">
                  <div className="label mb-1.5">Confidence</div>
                  <Badge tone={Number(r.confidence) > 0.85 ? "warn" : "bad"}>
                    {r.confidence}
                  </Badge>
                </div>
                <div className="flex gap-2">
                  <button className="btn-primary" disabled={busy === r.source_value}
                          onClick={() => decide(r, "confirm")}>
                    {busy === r.source_value ? "Saving" : "Same site"}
                  </button>
                  <button className="btn-ghost" disabled={busy === r.source_value}
                          onClick={() => decide(r, "reject")}>
                    Different
                  </button>
                </div>
              </div>
              <p className="text-[11px] text-mist-700 mt-4 pt-3 border-t border-line">
                Same country and principal investigator. The difference is an
                abbreviation.
              </p>
            </div>
          ))}
        </div>
      )}

      {decisions.length > 0 && (
        <Panel
          title="Audit trail"
          subtitle="Append-only. Every decision is kept with who made it and when; a revert
                    restores the automatic match without erasing what came before."
          right={<Badge tone="neutral">{decisions.length} entries</Badge>}
        >
          <div className="overflow-auto rounded-md border border-line" style={{ maxHeight: "24rem" }}>
            <table className="w-full text-sm border-collapse">
              <thead className="sticky top-0 z-10">
                <tr className="bg-ink-700">
                  {["When", "Who", "System", "Identifier", "Decision", "Site", "Status", ""]
                    .map((h) => (
                      <th key={h} className="text-left label font-medium px-3 py-2.5
                                             border-b border-line whitespace-nowrap">{h}</th>
                    ))}
                </tr>
              </thead>
              <tbody>
                {decisions.map((d, i) => (
                  <tr key={i} className={`border-b border-line/60 last:border-0
                                          ${d.in_effect ? "" : "opacity-45"}`}>
                    <td className="px-3 py-2.5 mono text-mist-500 whitespace-nowrap">
                      {String(d.decided_at || "").replace("T", " ").slice(0, 19)}
                    </td>
                    <td className="px-3 py-2.5 whitespace-nowrap">{d.decided_by}</td>
                    <td className="px-3 py-2.5 whitespace-nowrap">{d.system}</td>
                    <td className="px-3 py-2.5 mono text-mist-300">{d.source_value}</td>
                    <td className="px-3 py-2.5">
                      <Badge tone={d.decision === "confirm" ? "good"
                                 : d.decision === "reject" ? "bad" : "neutral"}>
                        {d.decision}
                      </Badge>
                    </td>
                    <td className="px-3 py-2.5 mono text-mist-300">
                      {d.canonical_site || "—"}
                    </td>
                    <td className="px-3 py-2.5 text-[11px] text-mist-500 whitespace-nowrap">
                      {d.in_effect ? "in effect" : "superseded"}
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      {d.revertable && (
                        <button
                          className="btn-ghost text-[12px] py-1 px-2.5"
                          disabled={busy === d.source_value}
                          onClick={() => revert(d)}
                        >
                          {busy === d.source_value ? "Reverting" : "Revert"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
    </div>
  );
}
