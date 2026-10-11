"""
load_to_tiger.py — push the harmonised output into Tiger Data (Postgres).

The pipeline still produces files; this loads them into a real database so the
application can read from Postgres instead. Only repository.py changes to use
it — nothing above that layer knows or cares which store is behind it.

Why Postgres here: the five source feeds are relational and the questions are
joins and aggregations, which is what SQL is for. Tiger Data is Postgres with
hypertables and continuous aggregates on top, so the trial's time-ordered data
(visits, shipments, invoices, adverse events) has somewhere to grow into
without changing engines.

Setup:
    pip install "psycopg[binary]" sqlalchemy
    export DATABASE_URL="postgres://tsdbadmin:...@....tsdb.cloud.timescale.com:xxxxx/tsdb?sslmode=require"
    python3 -m backend.pipeline.load_to_tiger
"""

import json
import os
import sys

import pandas as pd
from sqlalchemy import create_engine, text

from backend.core import config

TABLES = [
    "site_master", "crosswalk", "quality_issues",
    "resolved_edc_patients", "resolved_edc_adverse_events",
    "resolved_ctms_sites", "resolved_irt_supply",
    "resolved_safety_cases", "resolved_finance_payments",
]

# Feeds with a natural time column — candidates for Tiger hypertables.
TIME_COLUMNS = {
    "resolved_edc_adverse_events": "event_date",
    "resolved_safety_cases": "reported_date",
    "resolved_edc_patients": "enroll_date",
}


def engine():
    url = os.getenv("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set. Copy it from your Tiger Cloud service page.")
    # SQLAlchemy wants the postgresql+psycopg scheme
    url = url.replace("postgres://", "postgresql+psycopg://", 1) \
             .replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(url, pool_pre_ping=True)


def main():
    eng = engine()
    loaded = []

    with eng.begin() as conn:
        for name in TABLES:
            path = config.PROCESSED / f"{name}.csv"
            if not path.exists():
                print(f"  skip   {name} (not built)")
                continue
            df = pd.read_csv(path)
            df.to_sql(name, conn, if_exists="replace", index=False)
            loaded.append((name, len(df)))
            print(f"  loaded {name:32} {len(df):>6} rows")

        # Feed metadata and the catalog travel with the data.
        meta = pd.read_csv(config.RAW / "_feed_metadata.csv")
        meta.to_sql("feed_metadata", conn, if_exists="replace", index=False)

        with open(config.ANSWER_KEY) as f:
            key = json.load(f)
        pd.DataFrame(key["defects"]).to_sql("answer_key", conn,
                                            if_exists="replace", index=False)

        # Indexes on the join key every cross-system question uses.
        for name, _ in loaded:
            cols = pd.read_sql(text(f'SELECT * FROM "{name}" LIMIT 0'), conn).columns
            if "canonical_site" in cols:
                conn.execute(text(
                    f'CREATE INDEX IF NOT EXISTS idx_{name}_site '
                    f'ON "{name}" (canonical_site)'))
        conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_site_master_id ON site_master (site_id)'))

        # Tiger Data specifics. Harmless if the extension isn't present.
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
            for name, col in TIME_COLUMNS.items():
                if not any(n == name for n, _ in loaded):
                    continue
                cols = pd.read_sql(text(f'SELECT * FROM "{name}" LIMIT 0'), conn).columns
                if col not in cols:
                    continue
                conn.execute(text(
                    f'ALTER TABLE "{name}" ALTER COLUMN "{col}" '
                    f'TYPE timestamptz USING "{col}"::timestamptz'))
                conn.execute(text(
                    f"SELECT create_hypertable('{name}', '{col}', "
                    f"migrate_data => true, if_not_exists => true)"))
                print(f"  hypertable on {name}.{col}")
        except Exception as e:
            print(f"  (timescaledb features unavailable: {str(e)[:90]})")

    print(f"\nLoaded {len(loaded)} tables. Point the app at Postgres with:")
    print('  export OST_STORE=postgres')


if __name__ == "__main__":
    main()
