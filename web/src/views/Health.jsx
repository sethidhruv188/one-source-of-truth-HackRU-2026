import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Panel, Stat, Table, Spinner, Badge, Notice, WithheldNotice } from "../components/ui";
import { titleCase } from "../lib/format";

export default function Health() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => { api.quality().then(setData).catch((e) => setErr(e.message)); }, []);
  if (err) return <Notice tone="bad" title="Request failed">{err}</Notice>;
  if (!data) return <Spinner label="Running quality checks" />;

  const byType = data.issues.reduce((acc, i) => {
    (acc[i.type] ||= []).push(i);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl font-semibold tracking-tight">Data health</h1>
        <p className="text-sm text-mist-500 mt-1 max-w-3xl leading-relaxed">
          The feeds are deliberately corrupted before loading and the answer key is
          committed to the repository. This screen scores the pipeline against it.
        </p>
      </header>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat label="Issues detected" value={data.detected} />
        <Stat label="Planted defects caught" value={`${data.caught} / ${data.planted}`}
              tone={data.caught === data.planted ? "good" : "warn"}
              hint="measured, not asserted" />
        <Stat label="High severity" value={data.high} tone={data.high ? "bad" : "good"} />
        <Stat label="Stale feeds" value={data.feeds.filter((f) => f.stale).length}
              tone={data.feeds.some((f) => f.stale) ? "warn" : "good"} />
      </div>

      <WithheldNotice columns={data.withheld_columns} role={user.role} />

      <Panel title="Feed freshness"
             subtitle="Every answer is only as current as the feed behind it.">
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {data.feeds.map((f) => (
            <div key={f.feed} className="border border-line rounded-md px-4 py-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{f.system}</span>
                <Badge tone={f.stale ? "bad" : f.age_hours >= 24 ? "warn" : "good"}>
                  {f.age_hours >= 24 ? `${Math.floor(f.age_hours / 24)}d` : `${f.age_hours}h`} ago
                </Badge>
              </div>
              <div className="mono text-[11px] text-mist-700 mt-1.5">{f.feed}</div>
            </div>
          ))}
        </div>
      </Panel>

      {Object.entries(byType).map(([type, issues]) => (
        <Panel key={type} title={titleCase(type)}
               right={<Badge tone={issues[0].severity === "high" ? "bad" : "warn"}>
                 {issues.length}
               </Badge>}>
          <Table rows={issues} dense maxHeight="16rem"
                 columns={["feed", "key", "severity", "detail", "source_row"]} />
        </Panel>
      ))}
    </div>
  );
}
