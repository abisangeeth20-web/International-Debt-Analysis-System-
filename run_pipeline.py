"""End-to-end pipeline:
raw CSV -> DataFrame -> cleaning -> normalised tables -> SQLite (+ MySQL)
-> 30 SQL queries -> EDA tables & charts -> Power BI extracts -> summary JSON.

Usage:
    python run_pipeline.py            # SQLite only (no server needed)
    python run_pipeline.py --mysql    # also load MySQL and run the queries there
                                      # (set DEBT_DB_PASS / DEBT_DB_USER / DEBT_DB_HOST first)
"""
from __future__ import annotations

import argparse
import json
import sys

from src import config, database, eda, plotting, powerbi_export, preprocessing, sql_runner


def main(use_mysql: bool = False) -> dict:
    print("=" * 64, "\nSTEP 1  Data collection (CSV -> DataFrame)")
    raw = preprocessing.load_raw()
    raw_profile = preprocessing.profile(raw)
    print(f"  raw shape {raw.shape}, countries {raw_profile['unique_countries']}, "
          f"indicators {raw_profile['unique_indicators']}, nulls {sum(raw_profile['null_counts'].values())}")

    print("STEP 2  Preprocessing")
    debt_df, macro_df, clean_log = preprocessing.clean(raw)
    meta = preprocessing.load_country_metadata()
    countries, indicators, fact, macro = preprocessing.build_dimensions(debt_df, macro_df, meta)
    tables = {"countries": countries, "indicators": indicators, "debt_data": fact, "country_macro": macro}
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    cleaned = debt_df.merge(countries[["country_code", "region", "income_group"]], on="country_code")
    cleaned.to_csv(config.CLEANED_CSV, index=False)
    macro_df.to_csv(config.MACRO_CSV, index=False)
    countries.to_csv(config.COUNTRIES_CSV, index=False)
    indicators.to_csv(config.INDICATORS_CSV, index=False)
    for k, v in clean_log.items():
        print(f"  {k:<28} {v}")

    print("STEP 3  Database (SQLite, PK/FK enforced)")
    sqlite_counts = database.build_sqlite(tables)
    print(f"  {sqlite_counts}")
    mysql_counts = None
    if use_mysql:
        print("        Database (MySQL)")
        mysql_counts = database.build_mysql(tables)
        print(f"  {mysql_counts}")

    print("STEP 4  30 SQL analytical queries")
    status = sql_runner.run_all(database.sqlite_query, "SQLite (data/processed/international_debt.db)")
    if use_mysql:
        mysql_status = sql_runner.run_all(database.mysql_query, "MySQL 8 (international_debt)")
        mismatch = (status["rows"] != mysql_status["rows"]).sum()
        print(f"  MySQL and SQLite row counts differ for {mismatch} queries")
        status = mysql_status
    print(f"  {len(status)} queries executed -> sql_outputs/")

    print("STEP 5  EDA")
    df = eda.full_frame(tables)
    cs = eda.country_summary(df, macro)
    ind = eda.indicator_summary(df)
    grp = eda.group_summary(df)
    region = eda.segment_summary(cs, "region")
    income = eda.segment_summary(cs, "income_group")
    corr = eda.correlations(cs)
    stats = eda.statistics(df, cs)
    found = eda.findings(cs, ind, grp, region, income)
    config.EDA_TABLES_DIR.mkdir(parents=True, exist_ok=True)
    cs.round(4).to_csv(config.EDA_TABLES_DIR / "country_summary.csv", index=False)
    ind.round(4).to_csv(config.EDA_TABLES_DIR / "indicator_summary.csv", index=False)
    grp.round(4).to_csv(config.EDA_TABLES_DIR / "indicator_group_summary.csv", index=False)
    region.round(4).to_csv(config.EDA_TABLES_DIR / "region_summary.csv", index=False)
    income.round(4).to_csv(config.EDA_TABLES_DIR / "income_group_summary.csv", index=False)
    corr.to_csv(config.EDA_TABLES_DIR / "correlation_matrix.csv")

    q75, q25 = stats["country_total_q75_usd"], stats["country_total_q25_usd"]
    for name, actual, used in [("HIGH", q75, config.HIGH_DEBT_THRESHOLD), ("LOW", q25, config.LOW_DEBT_THRESHOLD)]:
        if abs(actual - used) / actual > 0.05:
            print(f"  WARNING: {name} threshold {used:,.0f} is far from the percentile {actual:,.0f}")

    print("STEP 6  Charts")
    figs = plotting.make_all(df, cs, ind, grp, region, corr)
    print(f"  {len(figs)} charts -> reports/figures/")

    print("STEP 7  Power BI extracts")
    pbi = powerbi_export.export(tables, df, cs, ind, grp)
    print(f"  {len(pbi)} CSV files -> powerbi_data/")

    summary = {
        "raw_profile": raw_profile, "cleaning": clean_log, "sqlite_rows": sqlite_counts,
        "mysql_rows": mysql_counts, "queries": status.to_dict("records"), "statistics": stats,
        "findings": found, "thresholds": {"high_usd": config.HIGH_DEBT_THRESHOLD, "low_usd": config.LOW_DEBT_THRESHOLD},
        "figures": figs, "powerbi_files": pbi,
    }
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (config.REPORTS_DIR / "pipeline_summary.json").write_text(json.dumps(summary, indent=2, default=str),
                                                               encoding="utf-8")
    print("DONE -> reports/pipeline_summary.json")
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mysql", action="store_true", help="also load MySQL and run the queries there")
    args = p.parse_args()
    sys.exit(0 if main(args.mysql) else 1)
