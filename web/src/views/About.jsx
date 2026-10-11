import { Panel } from "../components/ui";

const PIPELINE = [
  ["fetch_public", "ClinicalTrials.gov and openFDA, with graceful fallback"],
  ["build_data", "the real study becomes five disagreeing feeds, plus an answer key"],
  ["harmonize", "crosswalk, lineage stamps, quality checks, wide table"],
  ["graph_builder", "sites, patients, aliases, one node per source row"],
  ["catalog_builder", "FAIR metadata and column profiling"],
];

const SOURCES = [
  ["EDC — patients, adverse events", "Real", "CDISC SDTM/ADaM pilot, study CDISCPILOT01"],
  ["CTMS — facility names", "Real", "ClinicalTrials.gov API v2"],
  ["Adverse event terminology", "Real", "openFDA FAERS MedDRA reaction terms"],
  ["IRT, finance, operational fields", "Synthetic", "Derived from the same sites so a correct answer exists"],
];

export default function About() {
  return (
    <div className="space-y-6 max-w-4xl">
      <header>
        <h1 className="text-xl font-semibold tracking-tight">How it works</h1>
      </header>

      <Panel title="The problem">
        <p className="text-sm text-mist-300 leading-relaxed">
          A trial's data lives in separate systems and none of them use the same
          identifiers. The same hospital is <span className="mono text-mist-100">SITE-0701</span> in
          the EDC, <span className="mono text-mist-100">701</span> in the CTMS,{" "}
          <span className="mono text-mist-100">S701</span> in drug supply, and{" "}
          <span className="mono text-mist-100">Mercy General Hospital</span> in finance.
          Answering one cross-system question takes weeks of spreadsheet reconciliation,
          and the answer still isn't traceable.
        </p>
      </Panel>

      <Panel title="Architecture"
             subtitle="Access control lives in the service layer, not the interface.">
        <pre className="mono text-mist-300 leading-relaxed bg-ink-900 border border-line
                        rounded-md p-4 overflow-auto">{`web/          React. Renders only. Never reads the database.
   | HTTP
api.py        FastAPI. Translates HTTP to Python. No rules.
   |
services.py   Business logic + ACCESS CONTROL
   |
repository.py The only module that touches stored data
   |
database/     raw feeds, harmonised output, graph, catalog`}</pre>
        <p className="text-sm text-mist-300 mt-4 leading-relaxed">
          A column a role may not see is removed before the response is built, so it
          never reaches the browser. There is nothing for the interface to hide.
          Swapping file storage for Postgres means rewriting one module.
        </p>
      </Panel>

      <Panel title="Pipeline">
        <div className="space-y-2.5">
          {PIPELINE.map(([name, what], i) => (
            <div key={name} className="flex gap-4 items-baseline">
              <span className="mono text-mist-700 text-xs w-5">{i + 1}</span>
              <span className="mono text-accent text-[13px] w-36 shrink-0">{name}</span>
              <span className="text-sm text-mist-300">{what}</span>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Data sources"
             subtitle="No individual is identifiable. The clinical data is de-identified and every person name is generated.">
        <div className="space-y-3">
          {SOURCES.map(([feed, kind, note]) => (
            <div key={feed} className="flex gap-4 items-baseline border-b border-line/60 pb-3 last:border-0">
              <span className={`chip border shrink-0 ${kind === "Real"
                ? "bg-good/10 text-good border-good/25" : "bg-ink-600 text-mist-500 border-line"}`}>
                {kind}
              </span>
              <div>
                <div className="text-sm text-mist-100">{feed}</div>
                <div className="text-xs text-mist-500 mt-0.5">{note}</div>
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Standards">
        <div className="space-y-3 text-sm">
          {[["FAIR (Wilkinson et al. 2016)",
             "Persistent identifiers, column-level metadata, per-dataset licence and provenance. Metadata stays visible where data is restricted."],
            ["CDISC SDTM", "Clinical feeds map to SDTM domains."],
            ["OHDSI / OMOP",
             "Identity resolution follows the source_to_concept_map pattern, exposed in that shape in the catalog."]].map(([k, v]) => (
            <div key={k}>
              <div className="text-mist-100 font-medium">{k}</div>
              <div className="text-mist-500 text-[13px] mt-0.5 leading-relaxed">{v}</div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
