import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { Panel, Stat, Spinner, Badge, Notice, Table } from "../components/ui";

const COLOUR = { Site: "#4a8fe7", Alias: "#c99a3c", Patient: "#3fa776", Record: "#5b6775" };
const SIZE   = { Site: 11, Alias: 6, Patient: 4, Record: 2.6 };

/** Force-directed layout in a canvas. No external graph library. */
function Canvas({ data, onHover }) {
  const ref = useRef(null);
  const state = useRef({ nodes: [], links: [] });

  useEffect(() => {
    const W = 1100, H = 520;
    const nodes = data.nodes.map((n, i) => ({
      ...n,
      x: W / 2 + Math.cos((i / data.nodes.length) * 6.283) * 200 + Math.random() * 20,
      y: H / 2 + Math.sin((i / data.nodes.length) * 6.283) * 200 + Math.random() * 20,
      vx: 0, vy: 0,
    }));
    const index = new Map(nodes.map((n) => [n.id, n]));
    const links = data.links
      .map((l) => ({ s: index.get(l.source), t: index.get(l.target), kind: l.kind }))
      .filter((l) => l.s && l.t);
    state.current = { nodes, links };

    const canvas = ref.current;
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = "100%"; canvas.style.height = `${H}px`;
    ctx.scale(dpr, dpr);

    let frame, alpha = 1;
    function tick() {
      alpha *= 0.985;
      // repulsion
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j];
          let dx = b.x - a.x, dy = b.y - a.y;
          let d2 = dx * dx + dy * dy || 1;
          if (d2 > 42000) continue;
          const f = (900 * alpha) / d2;
          const d = Math.sqrt(d2);
          a.vx -= (dx / d) * f; a.vy -= (dy / d) * f;
          b.vx += (dx / d) * f; b.vy += (dy / d) * f;
        }
      }
      // springs
      for (const l of links) {
        const dx = l.t.x - l.s.x, dy = l.t.y - l.s.y;
        const d = Math.hypot(dx, dy) || 1;
        const f = ((d - (l.kind === "alias_of" ? 70 : 42)) * 0.012 * alpha);
        l.s.vx += (dx / d) * f; l.s.vy += (dy / d) * f;
        l.t.vx -= (dx / d) * f; l.t.vy -= (dy / d) * f;
      }
      for (const n of nodes) {
        if (n.kind === "Site") { n.vx += (W / 2 - n.x) * 0.02; n.vy += (H / 2 - n.y) * 0.02; }
        n.vx += (W / 2 - n.x) * 0.0012; n.vy += (H / 2 - n.y) * 0.0012;
        n.x += (n.vx *= 0.82); n.y += (n.vy *= 0.82);
        n.x = Math.max(16, Math.min(W - 16, n.x));
        n.y = Math.max(16, Math.min(H - 16, n.y));
      }

      ctx.clearRect(0, 0, W, H);
      for (const l of links) {
        ctx.strokeStyle = l.kind === "alias_of" ? "rgba(201,154,60,.55)" : "rgba(43,51,62,.9)";
        ctx.lineWidth = l.kind === "alias_of" ? 1.4 : 0.7;
        ctx.beginPath(); ctx.moveTo(l.s.x, l.s.y); ctx.lineTo(l.t.x, l.t.y); ctx.stroke();
      }
      for (const n of nodes) {
        ctx.fillStyle = COLOUR[n.kind] || "#666";
        ctx.beginPath(); ctx.arc(n.x, n.y, SIZE[n.kind] || 3, 0, 6.283); ctx.fill();
        if (n.kind === "Site" || n.kind === "Alias") {
          ctx.fillStyle = n.kind === "Site" ? "#e8ecf1" : "#aeb8c4";
          ctx.font = `${n.kind === "Site" ? 600 : 400} ${n.kind === "Site" ? 12 : 10}px Inter, sans-serif`;
          ctx.fillText(String(n.label).slice(0, 26), n.x + SIZE[n.kind] + 5, n.y + 3.5);
        }
      }
      frame = requestAnimationFrame(tick);
    }
    tick();
    return () => cancelAnimationFrame(frame);
  }, [data]);

  function move(e) {
    const r = ref.current.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * 1100;
    const y = ((e.clientY - r.top) / r.height) * 520;
    let best = null, bd = 220;
    for (const n of state.current.nodes) {
      const d = (n.x - x) ** 2 + (n.y - y) ** 2;
      if (d < bd) { bd = d; best = n; }
    }
    onHover(best);
  }

  return <canvas ref={ref} onMouseMove={move} onMouseLeave={() => onHover(null)}
                 className="rounded-md bg-ink-900 border border-line cursor-crosshair" />;
}

export default function Graph() {
  const [params, setParams] = useSearchParams();
  const [stats, setStats] = useState(null);
  const [sites, setSites] = useState([]);
  const [site, setSite] = useState(params.get("site") || "");
  const [data, setData] = useState(null);
  const [hover, setHover] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.graphStats().then(setStats);
    api.sites().then((s) => {
      setSites(s.rows);
      if (!site && s.rows.length) setSite(String(s.rows[0].site_id));
    });
  }, []);

  useEffect(() => {
    if (!site) return;
    setData(null); setErr("");
    setParams({ site }, { replace: true });
    api.graphSite(site).then(setData).catch((e) => setErr(e.message));
  }, [site]);

  const aliases = useMemo(
    () => data?.nodes.filter((n) => n.kind === "Alias") ?? [], [data]);

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between gap-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Graph</h1>
          <p className="text-sm text-mist-500 mt-1 max-w-3xl leading-relaxed">
            Every source row is a node. Entities point back to the rows they were built
            from, so lineage is a single hop rather than a separate system.
          </p>
        </div>
        <select className="input w-auto" value={site} onChange={(e) => setSite(e.target.value)}>
          {sites.map((s) => (
            <option key={s.site_id} value={s.site_id}>{s.site_id} — {s.site_name}</option>
          ))}
        </select>
      </header>

      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
          <Stat label="Nodes" value={stats.nodes.toLocaleString()} />
          <Stat label="Edges" value={stats.edges.toLocaleString()} />
          {Object.entries(stats.by_kind).map(([k, v]) => (
            <Stat key={k} label={k} value={v.toLocaleString()} />
          ))}
        </div>
      )}

      {err && <Notice tone="bad">{err}</Notice>}

      <Panel title="Neighbourhood"
             subtitle="One site, the identifiers every system uses for it, its patients, and the source rows behind them."
             right={
               <div className="flex gap-3 text-[11px] text-mist-500">
                 {Object.entries(COLOUR).map(([k, c]) => (
                   <span key={k} className="flex items-center gap-1.5">
                     <span className="h-2 w-2 rounded-full" style={{ background: c }} />{k}
                   </span>
                 ))}
               </div>}>
        {!data ? <Spinner label="Building layout" /> : (
          <div className="relative">
            <Canvas data={data} onHover={setHover} />
            {hover && (
              <div className="absolute top-3 left-3 panel px-3 py-2 text-xs pointer-events-none">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full" style={{ background: COLOUR[hover.kind] }} />
                  <span className="font-medium">{hover.kind}</span>
                </div>
                <div className="mono text-mist-300 mt-1">{hover.label || hover.id}</div>
                {hover.source_file && (
                  <div className="mono text-mist-700 mt-0.5">
                    {hover.source_file} row {hover.source_row}
                  </div>
                )}
                {hover.system && (
                  <div className="text-mist-700 mt-0.5">
                    {hover.system} · confidence {hover.confidence}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </Panel>

      {aliases.length > 0 && (
        <Panel title={`This one site is known by ${aliases.length} identifiers`}>
          <Table dense rows={aliases.map((a) => ({
            system: a.system, identifier: a.label, confidence: a.confidence,
          }))} />
        </Panel>
      )}
    </div>
  );
}
