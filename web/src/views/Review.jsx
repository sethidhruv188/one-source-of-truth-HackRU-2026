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

  if (err) return <Notice tone="bad" title="Request failed">{err}</Notice>;
  if (!data) return <Spinner label="Loading review queue" />;

  const { stats, pending, decisions } = data;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl font-semibold tracking-tight">Review queue</h1>
        <p className="text-sm text-mist-500 mt-1 max-w-3xl leading-relaxed">
          Deterministic matches resolve automatically. Anything below 95% confidence stops
          here, because a wrong site merge silently corrupts every downstream number.
        </p>
      </header>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat label="Identifiers seen" value={stats.total} />
        <Stat label="Auto-matched" value={`${Math.round(stats.auto_pct * 100)}%`}
              hint={`${stats.auto} of ${stats.total}`} tone="good" />
        <Stat label="Awaiting a human" value={stats.pending}
              tone={stats.pending ? "warn" : "good"} />
        <Stat label="Decisions recorded" value={decisions.length} />
      </div>

      {pending.length === 0 ? (
        <Panel title="Queue clear">
          <Empty>Nothing is waiting for review.</Empty>
        </Panel>
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
                  <Badge tone={Number(r.confidence) > 0.85 ? "warn" : "bad"}>{r.confidence}</Badge>
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
                Same country and principal investigator. The difference is an abbreviation.
              </p>
            </div>
          ))}
        </div>
      )}

      {decisions.length > 0 && (
        <Panel title="Decision log"
               subtitle="Persisted to disk and reapplied on every rebuild. The system never asks the same question twice.">
          <Table rows={decisions} dense maxHeight="18rem" />
        </Panel>
      )}
    </div>
  );
}
