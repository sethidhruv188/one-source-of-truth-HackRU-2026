import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Panel, Table, Spinner, WithheldNotice, Notice, Badge, Sql, Empty } from "../components/ui";

const SUGGESTIONS = [
  "Which sites are running out of drug?",
  "Which sites have safety issues and overdue payments?",
  "Average kits remaining by country",
  "Top 5 sites by adverse events per patient",
];

function Lineage({ siteId, role }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    setData(null);
    api.lineage(siteId).then(setData).catch((e) => setErr(e.message));
  }, [siteId]);

  if (err) return <Notice tone="bad">{err}</Notice>;
  if (!data) return <Spinner label="Tracing sources" />;

  return (
    <div className="space-y-5">
      <div>
        <div className="label mb-2">Known by {data.aliases.length} identifiers</div>
        <Table rows={data.aliases} dense maxHeight="12rem"
               columns={["system", "identifier", "method", "confidence", "status"]} />
      </div>
      <div>
        <div className="label mb-2">
          Assembled from {data.sources.length} source rows across{" "}
          {new Set(data.sources.map((s) => s.system)).size} systems
        </div>
        <Table rows={data.sources} dense maxHeight="20rem"
               columns={["system", "source_file", "source_row", "record"]} />
      </div>
    </div>
  );
}

export default function Ask() {
  const { user } = useAuth();
  const [mode, setMode] = useState("free");
  const [questions, setQuestions] = useState([]);
  const [selected, setSelected] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState("");
  const [nlOn, setNlOn] = useState(true);
  const [trace, setTrace] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    api.questions().then((qs) => {
      setQuestions(qs);
      const landing = qs.find((q) => q.key === user.landing_question) || qs[0];
      if (landing) setSelected(landing.key);
    });
    api.nlAvailable().then((r) => { setNlOn(r.available); if (!r.available) setMode("preset"); });
  }, []);

  useEffect(() => {
    if (mode !== "preset" || !selected) return;
    setLoading(true); setErr(""); setTrace("");
    api.ask(selected)
      .then((r) => { setResult(r); setTrace(r.site_ids?.[0] || ""); })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
  }, [selected, mode]);

  async function submit(e) {
    e?.preventDefault();
    if (!question.trim()) return;
    setLoading(true); setErr(""); setResult(null); setTrace("");
    try {
      const r = await api.askFree(question);
      setResult(r);
      setTrace(r.site_ids?.[0] || "");
    } catch (e) { setErr(e.message); }
    setLoading(false);
  }

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Ask</h1>
          <p className="text-sm text-mist-500 mt-1">
            Questions that span every system, answered in under a second.
          </p>
        </div>
        <div className="flex rounded-md border border-line overflow-hidden text-[13px]">
          {[["free", "Ask anything"], ["preset", "Prepared questions"]].map(([k, label]) => (
            <button key={k} onClick={() => { setMode(k); setResult(null); setErr(""); }}
                    disabled={k === "free" && !nlOn}
                    className={`px-4 py-2 transition-colors disabled:opacity-40 ${
                      mode === k ? "bg-accent-soft text-accent font-medium"
                                 : "text-mist-500 hover:text-mist-100 hover:bg-ink-600"}`}>
              {label}
            </button>
          ))}
        </div>
      </header>

      {mode === "free" ? (
        <Panel>
          <form onSubmit={submit} className="flex gap-2">
            <input className="input flex-1" value={question} autoFocus
                   onChange={(e) => setQuestion(e.target.value)}
                   placeholder="e.g. which sites enrolled well but are low on drug?" />
            <button className="btn-primary px-5" disabled={loading || !question.trim()}>
              {loading ? "Working" : "Ask"}
            </button>
          </form>
          <div className="flex flex-wrap gap-2 mt-3">
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => { setQuestion(s); }}
                      className="px-3 py-1.5 rounded-md border border-line text-[12px] text-mist-500
                                 hover:border-accent/40 hover:text-accent hover:bg-accent-soft transition">
                {s}
              </button>
            ))}
          </div>
          <p className="text-[11px] text-mist-700 mt-4 leading-relaxed">
            The model writes the query. The database returns the numbers. No figure
            passes through the model, and the generated SQL is always shown.
          </p>
        </Panel>
      ) : (
        <Panel>
          <label className="label block mb-2">Question</label>
          <select className="input" value={selected} onChange={(e) => setSelected(e.target.value)}>
            {questions.map((q) => <option key={q.key} value={q.key}>{q.label}</option>)}
          </select>
          {questions.length < 6 && (
            <p className="text-[11px] text-mist-700 mt-3">
              {questions.length} of 6 questions are available to {user.role}. The rest
              depend on fields this role cannot see.
            </p>
          )}
        </Panel>
      )}

      {err && <Notice tone="bad" title="Request failed">{err}</Notice>}
      {loading && <Spinner label="Querying across five systems" />}

      {result && !loading && (
        <>
          {result.error ? (
            <Notice tone="warn" title="Not answerable">
              {result.error}
              <span className="block mt-2 text-mist-500">
                The system declines rather than guessing. In a regulated setting a
                confident wrong number is worse than no number.
              </span>
            </Notice>
          ) : (
            <>
              <WithheldNotice columns={result.withheld_columns} role={user.role} />

              <Panel title={result.label || "Result"}
                     right={<div className="flex gap-2">
                       <Badge tone="neutral">{result.rows?.length ?? 0} rows</Badge>
                       {result.systems && <Badge tone="accent">{result.systems.length} systems joined</Badge>}
                     </div>}>
                {result.explanation && (
                  <p className="text-sm text-mist-300 mb-4 leading-relaxed">{result.explanation}</p>
                )}
                {result.note ? <Empty>{result.note}</Empty> : <Table rows={result.rows} />}
              </Panel>

              {result.sql && (
                <Panel title="Generated query"
                       subtitle="Shown so the answer can be checked rather than trusted.">
                  <Sql>{result.sql}</Sql>
                </Panel>
              )}

              {result.site_ids?.length > 0 && (
                <Panel title="Where did this come from?"
                       subtitle="Every number traces back to the exact rows that produced it."
                       right={
                         <select className="input w-auto py-1.5 text-[13px]"
                                 value={trace} onChange={(e) => setTrace(e.target.value)}>
                           {result.site_ids.map((s) => <option key={s} value={s}>Site {s}</option>)}
                         </select>}>
                  {trace && <Lineage siteId={trace} role={user.role} />}
                </Panel>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
