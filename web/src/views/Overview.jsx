import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis,
         CartesianGrid, Tooltip, Cell } from "recharts";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Panel, Stat, Table, Spinner, WithheldNotice, Badge } from "../components/ui";

export default function Overview() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [kpis, setKpis] = useState(null);
  const [sites, setSites] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.kpis(), api.sites()])
      .then(([k, s]) => { setKpis(k); setSites(s); })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <Panel title="Error">{error}</Panel>;
  if (!kpis || !sites) return <Spinner label="Loading trial overview" />;

  const rows = sites.rows;
  const hasPatients = "enrolled_patients" in (rows[0] || {});
  const hasSupply = "kits_remaining" in (rows[0] || {});

  const atRisk = rows.filter(
    (r) => (r.kits_remaining ?? 99) < 15 ||
           (r.open_safety_cases ?? 0) > 0 ||
           (r.days_payment_overdue ?? 0) > 30
  );

  const scatter = rows.map((r) => ({
    ...r,
    x: r.enrolled_patients ?? r.enrollment_target ?? 0,
    y: r.kits_remaining ?? 0,
    risk: (r.kits_remaining ?? 99) < 10 ? "bad"
        : (r.kits_remaining ?? 99) < 20 ? "warn" : "good",
  }));

  const COLOUR = { bad: "#cf5f58", warn: "#c99a3c", good: "#3fa776" };

  const visible = [
    "site_id", "site_name",
    hasPatients && "enrolled_patients",
    "open_safety_cases", hasSupply && "kits_remaining",
    "days_payment_overdue", "systems_contributing",
  ].filter(Boolean).filter((c) => c in (rows[0] || {}));

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Trial overview</h1>
          <p className="text-sm text-mist-500 mt-1">
            Study CDISCPILOT01 · {kpis.sites} active sites · five source systems
          </p>
        </div>
        <Badge tone="accent">{user.role}</Badge>
      </header>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <Stat label="Sites" value={kpis.sites} />
        {kpis.patients !== undefined && <Stat label="Patients" value={kpis.patients} />}
        {kpis.open_safety_cases !== undefined && (
          <Stat label="Open safety cases" value={kpis.open_safety_cases}
                tone={kpis.open_safety_cases > 0 ? "warn" : "good"} />
        )}
        <Stat label="Identifiers auto-matched" value={`${kpis.auto_matched_pct}%`}
              hint={`${kpis.pending_review} awaiting review`} />
        <Stat label="Defects caught" value={`${kpis.defects_caught}/${kpis.defects_planted}`}
              tone="good" hint="against a planted answer key" />
      </div>

      <WithheldNotice columns={sites.withheld_columns} role={user.role} />

      {hasSupply && (
        <Panel title="Enrollment against drug supply"
               subtitle="Each point is one site. Sites in the lower right are enrolling well but running out of kits.">
          <ResponsiveContainer width="100%" height={260}>
            <ScatterChart margin={{ top: 8, right: 16, bottom: 18, left: 8 }}>
              <CartesianGrid stroke="#232a33" />
              <XAxis type="number" dataKey="x" name="Patients" stroke="#7a8696"
                     tick={{ fontSize: 11 }}
                     label={{ value: hasPatients ? "Patients enrolled" : "Enrollment target",
                              position: "insideBottom", offset: -8,
                              fill: "#7a8696", fontSize: 11 }} />
              <YAxis type="number" dataKey="y" name="Kits" stroke="#7a8696"
                     tick={{ fontSize: 11 }}
                     label={{ value: "Kits remaining", angle: -90, position: "insideLeft",
                              fill: "#7a8696", fontSize: 11 }} />
              <Tooltip
                cursor={{ stroke: "#4a8fe7", strokeDasharray: "3 3" }}
                contentStyle={{ background: "#101419", border: "1px solid #232a33",
                                borderRadius: 6, fontSize: 12 }}
                labelStyle={{ color: "#e8ecf1" }}
                formatter={(v, n) => [v, n]}
                content={({ payload }) => {
                  if (!payload?.length) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="panel px-3 py-2 text-xs">
                      <div className="font-medium">{d.site_name}</div>
                      <div className="text-mist-500 mono mt-0.5">site {d.site_id}</div>
                      <div className="mt-1.5 text-mist-300">
                        {d.kits_remaining} kits remaining
                        {d.enrolled_patients !== undefined && ` · ${d.enrolled_patients} patients`}
                      </div>
                    </div>
                  );
                }} />
              <Scatter data={scatter} onClick={(d) => navigate(`/graph?site=${d.site_id}`)}>
                {scatter.map((d, i) => <Cell key={i} fill={COLOUR[d.risk]} />)}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </Panel>
      )}

      <Panel title="Sites needing attention"
             subtitle={`${atRisk.length} of ${rows.length} sites have low supply, an open safety case, or payments over 30 days late.`}
             right={<Badge tone={atRisk.length ? "warn" : "good"}>{atRisk.length} flagged</Badge>}>
        <Table rows={atRisk.length ? atRisk : rows} columns={visible}
               onRowClick={(r) => navigate(`/graph?site=${r.site_id}`)} />
        <p className="text-xs text-mist-700 mt-3">
          Select a site to trace it back to its source rows across every system.
        </p>
      </Panel>
    </div>
  );
}
