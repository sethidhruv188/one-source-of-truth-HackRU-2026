import { tone, titleCase, num, money } from "../lib/format";

export function Panel({ title, subtitle, right, children, className = "" }) {
  return (
    <section className={`panel ${className}`}>
      {(title || right) && (
        <header className="flex items-start justify-between gap-4 px-5 py-4 border-b border-line">
          <div>
            {title && <h2 className="text-sm font-semibold text-mist-100">{title}</h2>}
            {subtitle && <p className="text-xs text-mist-500 mt-1 max-w-2xl leading-relaxed">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function Stat({ label, value, hint, tone: t }) {
  const colour = t === "bad" ? "text-bad" : t === "warn" ? "text-warn"
               : t === "good" ? "text-good" : "text-mist-100";
  return (
    <div className="panel px-5 py-4">
      <div className="label">{label}</div>
      <div className={`text-2xl font-semibold mt-2 tabular-nums ${colour}`}>{value}</div>
      {hint && <div className="text-xs text-mist-700 mt-1">{hint}</div>}
    </div>
  );
}

export function Badge({ tone: t = "neutral", children }) {
  const map = {
    good:    "bg-good/10 text-good border-good/25",
    warn:    "bg-warn/10 text-warn border-warn/25",
    bad:     "bg-bad/10 text-bad border-bad/25",
    accent:  "bg-accent-soft text-accent border-accent/25",
    neutral: "bg-ink-600 text-mist-300 border-line",
  };
  return <span className={`chip border ${map[t]}`}>{children}</span>;
}

export function Empty({ children }) {
  return (
    <div className="py-10 text-center text-sm text-mist-500 border border-dashed border-line rounded-md">
      {children}
    </div>
  );
}

export function Spinner({ label = "Loading" }) {
  return (
    <div className="flex items-center gap-3 py-8 text-sm text-mist-500">
      <span className="h-3.5 w-3.5 rounded-full border-2 border-mist-700 border-t-accent animate-spin" />
      {label}
    </div>
  );
}

export function Notice({ tone: t = "warn", title, children }) {
  const edge = t === "bad" ? "border-l-bad" : t === "good" ? "border-l-good"
             : t === "accent" ? "border-l-accent" : "border-l-warn";
  return (
    <div className={`border-l-2 ${edge} bg-ink-700/60 rounded-r-md px-4 py-3`}>
      {title && <div className="text-sm font-medium text-mist-100">{title}</div>}
      <div className="text-xs text-mist-300 mt-1 leading-relaxed">{children}</div>
    </div>
  );
}

const MONO_COLS = new Set([
  "site_id", "patient_id", "source_value", "identifier", "source_file",
  "source_row", "record", "key", "source_code", "target_concept_id", "column",
]);

export function Table({ rows, columns, onRowClick, maxHeight = "28rem", dense }) {
  if (!rows?.length) return <Empty>No rows</Empty>;
  const cols = columns || Object.keys(rows[0]);

  return (
    <div className="overflow-auto rounded-md border border-line" style={{ maxHeight }}>
      <table className="w-full text-sm border-collapse">
        <thead className="sticky top-0 z-10">
          <tr className="bg-ink-700">
            {cols.map((c) => (
              <th key={c}
                  className="text-left label font-medium px-3 py-2.5 border-b border-line whitespace-nowrap">
                {titleCase(c)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}
                onClick={onRowClick ? () => onRowClick(r) : undefined}
                className={`border-b border-line/60 last:border-0 transition-colors
                            ${onRowClick ? "cursor-pointer hover:bg-accent-soft" : "hover:bg-ink-700/50"}`}>
              {cols.map((c) => {
                const v = r[c];
                const t = tone(c, v);
                const display = c === "invoice_amount_usd" ? money(v) : num(v);
                return (
                  <td key={c}
                      className={`px-3 ${dense ? "py-1.5" : "py-2.5"} whitespace-nowrap
                                  ${MONO_COLS.has(c) ? "mono text-mist-300" : ""}
                                  ${t === "bad" ? "text-bad font-medium"
                                    : t === "warn" ? "text-warn" : "text-mist-100"}`}>
                    {v === null || v === undefined || v === "" ? (
                      <span className="text-mist-700">—</span>
                    ) : typeof v === "boolean" ? (
                      <Badge tone={v ? "bad" : "neutral"}>{v ? "yes" : "no"}</Badge>
                    ) : (
                      display
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function WithheldNotice({ columns, role }) {
  if (!columns?.length) return null;
  return (
    <Notice tone="warn" title={`${columns.length} field${columns.length > 1 ? "s" : ""} withheld from ${role}`}>
      <span className="mono text-warn">{columns.join(", ")}</span>
      <span className="block mt-1 text-mist-500">
        Filtered in the service layer. This data was never sent to the browser.
      </span>
    </Notice>
  );
}

export function Sql({ children }) {
  if (!children) return null;
  return (
    <pre className="mono bg-ink-900 border border-line rounded-md p-4 overflow-auto
                    text-mist-300 leading-relaxed whitespace-pre-wrap">
      {children}
    </pre>
  );
}
