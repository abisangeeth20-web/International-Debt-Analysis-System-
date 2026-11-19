"""CSV extracts for the Power BI dashboard (powerbi_data/).

The first eight files keep exactly the columns the existing .pbix was built
on, so Home -> Refresh in Power BI Desktop picks up the cleaned numbers.
The remaining files are extra tables for the additional report pages.
"""
from __future__ import annotations

import pandas as pd

from . import config


def export(tables: dict[str, pd.DataFrame], df: pd.DataFrame, cs: pd.DataFrame,
           ind: pd.DataFrame, grp: pd.DataFrame) -> dict[str, int]:
    out_dir = config.POWERBI_DATA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "countries.csv": tables["countries"][["country_id", "country_name", "country_code"]],
        "indicators.csv": tables["indicators"][["indicator_id", "indicator_code", "indicator_name"]],
        "debt_data.csv": tables["debt_data"][["debt_id", "country_id", "indicator_id", "debt_usd", "debt_billion_usd"]],
        "country_debt_summary.csv": cs.assign(
            total_debt_billion=cs["total_debt_billion"].round(2), pct_of_global=cs["pct_of_global"].round(4)
        )[["country_name", "country_code", "total_debt_billion", "pct_of_global", "debt_category", "debt_rank"]],
        "indicator_debt_summary.csv": ind.assign(
            total_debt_billion=ind["total_debt_billion"].round(2), pct_of_global=ind["pct_of_global"].round(4)
        )[["indicator_name", "indicator_code", "total_debt_billion", "pct_of_global"]],
        "country_indicator_matrix.csv": df.assign(debt_billion=df["debt_billion_usd"].round(4))[
            ["country_name", "country_code", "indicator_name", "indicator_code", "debt_billion"]
        ].sort_values("debt_billion", ascending=False),
        "debt_categories.csv": cs["debt_category"].value_counts().rename_axis("debt_category")
        .reset_index(name="country_count"),
        "kpi_summary.csv": pd.DataFrame([{
            "total_countries": len(tables["countries"]),
            "total_indicators": len(tables["indicators"]),
            "total_records": len(tables["debt_data"]),
            "total_debt_trillion": round(df["debt_usd"].sum() / 1e12, 4),
            "max_debt_billion": round(df["debt_usd"].max() / 1e9, 2),
            "avg_debt_billion": round(df["debt_usd"].mean() / 1e9, 4),
        }]),
        # extra tables
        "countries_enriched.csv": tables["countries"],
        "indicators_enriched.csv": tables["indicators"],
        "country_macro.csv": tables["country_macro"],
        "country_debt_profile.csv": cs[[
            "country_name", "country_code", "region", "income_group", "debt_rank", "debt_category",
            "total_debt_billion", "external_debt_stock_billion", "pct_of_global", "debt_to_gni_pct",
            "debt_to_exports_pct", "reserves_to_debt_pct", "cumulative_pct"]].round(4),
        "indicator_group_summary.csv": grp[["indicator_group", "indicators", "records", "total_debt_billion",
                                            "pct_of_global"]].round(4),
    }
    for name, frame in files.items():
        frame.to_csv(out_dir / name, index=False)
    return {k: len(v) for k, v in files.items()}
