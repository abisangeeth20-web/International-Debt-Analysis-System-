"""Parse the 30 analytical queries from sql/*.sql and run them."""
from __future__ import annotations

import re
from typing import Callable

import pandas as pd

from . import config


def parse_sql_file(path) -> list[dict]:
    """Split a .sql file into one dict per '-- Qn: title' block."""
    raw = path.read_text(encoding="utf-8")
    blocks = re.split(r"\n(?=-- Q\d+:)", raw)
    out = []
    for block in blocks:
        m = re.match(r"-- (Q\d+): (.+)", block)
        if not m:
            continue
        comments = [l[2:].strip() for l in block.splitlines()[1:] if l.startswith("--")]
        why = " ".join(comments).replace("Why:", "").strip()
        sql = "\n".join(l for l in block.splitlines() if not l.startswith("--")).strip().rstrip(";").strip()
        out.append({"id": m.group(1), "title": m.group(2).strip(), "why": why, "sql": sql})
    return out


def load_query_bank() -> list[dict]:
    bank = []
    for category, path in config.SQL_QUERY_FILES:
        for q in parse_sql_file(path):
            q["category"] = category
            bank.append(q)
    return bank


def run_all(run: Callable[[str], pd.DataFrame], engine_name: str, write_outputs: bool = True) -> pd.DataFrame:
    """Run every query with `run`; optionally save CSV / Excel / text evidence."""
    bank = load_query_bank()
    out_dir = config.SQL_OUTPUT_DIR
    if write_outputs:
        out_dir.mkdir(parents=True, exist_ok=True)
        for old in out_dir.glob("Q*.csv"):
            old.unlink()
    lines = [f"INTERNATIONAL DEBT ANALYSIS - 30 SQL QUERY EXECUTION REPORT", f"Engine: {engine_name}", "=" * 78]
    status = []
    results = {}
    for q in bank:
        df = run(q["sql"])
        results[q["id"]] = df
        status.append({"id": q["id"], "category": q["category"], "title": q["title"], "rows": len(df)})
        if write_outputs:
            slug = re.sub(r"[^a-zA-Z0-9]+", "_", q["title"]).strip("_").lower()[:50]
            df.to_csv(out_dir / f"{q['id']}_{slug}.csv", index=False)
            lines += ["", f"--- {q['id']} ({q['category']}): {q['title']} ---", f"Why: {q['why']}",
                      "SQL:", q["sql"], f"Rows returned: {len(df)}", df.head(10).to_string(index=False)]
            if len(df) > 10:
                lines.append(f"... {len(df) - 10} more rows in the CSV")
    if write_outputs:
        (out_dir / "query_execution_report.txt").write_text("\n".join(lines), encoding="utf-8")
        with pd.ExcelWriter(out_dir / "all_query_results.xlsx", engine="openpyxl") as xw:
            pd.DataFrame(status).to_excel(xw, sheet_name="Index", index=False)
            for qid, df in results.items():
                df.to_excel(xw, sheet_name=qid, index=False)
    return pd.DataFrame(status)
