import { useState } from "react";
import { useAuth } from "../lib/auth";

const DEMO = [
  { user: "dhruv",  role: "Study Manager",   note: "Full access to all five systems" },
  { user: "fiona",  role: "Finance Analyst", note: "No patient or safety data" },
  { user: "marcus", role: "Site Monitor",    note: "No financial data" },
  { user: "sana",   role: "Data Steward",    note: "Quality and identity matching" },
];

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(username, password);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Left: identity */}
      <div className="hidden lg:flex flex-col justify-between p-14 bg-ink-800 border-r border-line">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded bg-accent/15 border border-accent/30 grid place-items-center">
            <div className="h-2.5 w-2.5 rounded-sm bg-accent" />
          </div>
          <span className="text-sm font-semibold tracking-tight">One Source of Truth</span>
        </div>

        <div className="max-w-md">
          <h1 className="text-4xl font-semibold leading-tight tracking-tight">
            One trial.<br />Five systems.<br />
            <span className="text-mist-500">No shared IDs.</span>
          </h1>
          <p className="text-sm text-mist-500 mt-6 leading-relaxed">
            The same hospital is <span className="mono text-mist-300">SITE-0701</span> in the EDC,
            <span className="mono text-mist-300"> 701</span> in the CTMS,
            <span className="mono text-mist-300"> S701</span> in drug supply, and
            <span className="mono text-mist-300"> Mercy General Hospital</span> in finance.
            Answering one cross-system question takes weeks, and the answer isn't traceable.
          </p>
          <p className="text-sm text-mist-300 mt-5 leading-relaxed">
            This answers it in under a second, and every number traces back to the
            source row it came from.
          </p>
        </div>

        <div className="text-[11px] text-mist-700 leading-relaxed">
          Clinical data from the CDISC SDTM/ADaM pilot study, de-identified.
          Operational feeds synthetic. No individual is identifiable.
        </div>
      </div>

      {/* Right: form */}
      <div className="flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-3 mb-10">
            <div className="h-8 w-8 rounded bg-accent/15 border border-accent/30 grid place-items-center">
              <div className="h-2.5 w-2.5 rounded-sm bg-accent" />
            </div>
            <span className="text-sm font-semibold">One Source of Truth</span>
          </div>

          <h2 className="text-xl font-semibold tracking-tight">Sign in</h2>
          <p className="text-sm text-mist-500 mt-1.5">
            Your role determines what you can see.
          </p>

          <form onSubmit={submit} className="mt-8 space-y-4">
            <div>
              <label className="label block mb-2">Username</label>
              <input className="input" value={username} autoFocus autoComplete="username"
                     onChange={(e) => setUsername(e.target.value)} placeholder="dhruv" />
            </div>
            <div>
              <label className="label block mb-2">Password</label>
              <input className="input" type="password" value={password} autoComplete="current-password"
                     onChange={(e) => setPassword(e.target.value)} placeholder="demo" />
            </div>

            {error && (
              <div className="text-xs text-bad border-l-2 border-bad pl-3 py-1">{error}</div>
            )}

            <button className="btn-primary w-full" disabled={busy || !username || !password}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <div className="mt-10 pt-6 border-t border-line">
            <div className="label mb-3">Demo accounts · password "demo"</div>
            <div className="space-y-1.5">
              {DEMO.map((d) => (
                <button key={d.user} type="button"
                        onClick={() => { setUsername(d.user); setPassword("demo"); }}
                        className="w-full text-left px-3 py-2 rounded-md border border-line
                                   hover:border-accent/40 hover:bg-accent-soft transition group">
                  <div className="flex items-center justify-between">
                    <span className="mono text-mist-100">{d.user}</span>
                    <span className="text-[11px] text-mist-500 group-hover:text-accent transition">
                      {d.role}
                    </span>
                  </div>
                  <div className="text-[11px] text-mist-700 mt-0.5">{d.note}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
