"""Database layer: build the relational DB (SQLite always, MySQL optionally)
and give the rest of the project one way to run SQL against it."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

TABLE_ORDER = ["countries", "indicators", "debt_data", "country_macro"]

SQLITE_SCHEMA = """
PRAGMA foreign_keys = ON;
DROP VIEW IF EXISTS vw_top10_countries;
DROP VIEW IF EXISTS vw_country_debt_profile;
DROP TABLE IF EXISTS debt_data;
DROP TABLE IF EXISTS country_macro;
DROP TABLE IF EXISTS countries;
DROP TABLE IF EXISTS indicators;

CREATE TABLE countries (
    country_id       INTEGER PRIMARY KEY,
    country_code     TEXT NOT NULL UNIQUE,
    country_name     TEXT NOT NULL,
    region           TEXT NOT NULL,
    income_group     TEXT NOT NULL,
    lending_category TEXT NOT NULL
);
CREATE TABLE indicators (
    indicator_id    INTEGER PRIMARY KEY,
    indicator_code  TEXT NOT NULL UNIQUE,
    indicator_name  TEXT NOT NULL,
    indicator_group TEXT NOT NULL
);
CREATE TABLE debt_data (
    debt_id          INTEGER PRIMARY KEY,
    country_id       INTEGER NOT NULL REFERENCES countries(country_id),
    indicator_id     INTEGER NOT NULL REFERENCES indicators(indicator_id),
    debt_usd         REAL NOT NULL,
    debt_billion_usd REAL NOT NULL,
    UNIQUE (country_id, indicator_id)
);
CREATE TABLE country_macro (
    country_id          INTEGER PRIMARY KEY REFERENCES countries(country_id),
    gni_usd             REAL,
    exports_usd         REAL,
    imports_usd         REAL,
    reserves_usd        REAL,
    current_account_usd REAL
);
CREATE INDEX idx_debt_indicator ON debt_data(indicator_id);
CREATE INDEX idx_indicator_group ON indicators(indicator_group);
"""


def _views_sql() -> list[str]:
    """CREATE VIEW statements taken from the MySQL schema file (same SQL works in SQLite)."""
    text = (config.SQL_DIR / "00_schema.sql").read_text(encoding="utf-8")
    return [m.strip() for m in re.findall(r"(CREATE VIEW .*?;)", text, flags=re.S)]


def _rows(df: pd.DataFrame) -> list[tuple]:
    clean = df.astype(object).where(pd.notna(df), None)
    return [tuple(None if (isinstance(v, float) and np.isnan(v)) else v for v in row)
            for row in clean.itertuples(index=False, name=None)]


def build_sqlite(tables: dict[str, pd.DataFrame], path: Path = config.SQLITE_DB) -> dict:
    """Create the SQLite database with primary/foreign keys and load all tables."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SQLITE_SCHEMA)
        for name in TABLE_ORDER:
            df = tables[name]
            cols = ", ".join(df.columns)
            marks = ", ".join("?" for _ in df.columns)
            conn.executemany(f"INSERT INTO {name} ({cols}) VALUES ({marks})", _rows(df))
        for view in _views_sql():
            conn.execute(view)
        conn.commit()
        fk_problems = conn.execute("PRAGMA foreign_key_check").fetchall()
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLE_ORDER}
        conn.execute("VACUUM")
    finally:
        conn.close()
    if fk_problems:
        raise RuntimeError(f"Foreign key violations in SQLite: {fk_problems[:5]}")
    return counts


def build_mysql(tables: dict[str, pd.DataFrame]) -> dict:
    """Run sql/00_schema.sql on MySQL and insert the cleaned data (Python -> MySQL)."""
    import mysql.connector

    cfg = config.MYSQL
    conn = mysql.connector.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"],
                                   password=cfg["password"])
    cur = conn.cursor()
    script = (config.SQL_DIR / "00_schema.sql").read_text(encoding="utf-8")
    script = "\n".join(l for l in script.splitlines() if not l.strip().startswith("--"))
    script = script.replace("international_debt", cfg["database"])
    statements = [s.strip() for s in script.split(";") if s.strip()]
    views = [s for s in statements if s.upper().startswith("CREATE VIEW")]
    for stmt in statements:
        if stmt not in views:
            cur.execute(stmt)
    for name in TABLE_ORDER:
        df = tables[name]
        cols = ", ".join(df.columns)
        marks = ", ".join(["%s"] * len(df.columns))
        rows = _rows(df)
        for i in range(0, len(rows), 5000):
            cur.executemany(f"INSERT INTO {name} ({cols}) VALUES ({marks})", rows[i:i + 5000])
    for view in views:
        cur.execute(view)
    conn.commit()
    counts = {}
    for name in TABLE_ORDER:
        cur.execute(f"SELECT COUNT(*) FROM {name}")
        counts[name] = cur.fetchone()[0]
    cur.close()
    conn.close()
    return counts


# ── Query helpers ─────────────────────────────────────────────
def sqlite_query(sql: str, path: Path = config.SQLITE_DB) -> pd.DataFrame:
    conn = sqlite3.connect(path)
    try:
        return pd.read_sql_query(sql, conn)
    finally:
        conn.close()


def mysql_query(sql: str) -> pd.DataFrame:
    import mysql.connector

    cfg = config.MYSQL
    conn = mysql.connector.connect(**cfg)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [c[0] for c in cur.description]
        data = cur.fetchall()
        cur.close()
        return pd.DataFrame(data, columns=cols)
    finally:
        conn.close()


def load_tables_from_sqlite(path: Path = config.SQLITE_DB) -> dict[str, pd.DataFrame]:
    return {t: sqlite_query(f"SELECT * FROM {t}", path) for t in TABLE_ORDER}
