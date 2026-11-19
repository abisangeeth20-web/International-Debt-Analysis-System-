"""Exploratory data analysis: summary tables and computed findings."""
from __future__ import annotations

import pandas as pd

from . import config


def full_frame(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Denormalised view: one row per debt record with country + indicator attributes."""
    return (
        tables["debt_data"]
        .merge(tables["countries"], on="country_id")
        .merge(tables["indicators"], on="indicator_id")
    )


def categorize(total_usd: pd.Series) -> pd.Series:
    return pd.cut(
        total_usd,
        bins=[-float("inf"), config.LOW_DEBT_THRESHOLD, config.HIGH_DEBT_THRESHOLD, float("inf")],
        labels=["Low Debt", "Medium Debt", "High Debt"], right=False,
    ).astype(str)


def country_summary(df: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["country_id", "country_name", "country_code", "region", "income_group"], as_index=False)
    out = g.agg(total_debt_usd=("debt_usd", "sum"), records=("debt_id", "count"))
    stock = df[df["indicator_code"] == config.TOTAL_EXTERNAL_DEBT_CODE][["country_id", "debt_usd"]]
    out = out.merge(stock.rename(columns={"debt_usd": "external_debt_stock_usd"}), on="country_id", how="left")
    out = out.merge(macro[["country_id", "gni_usd", "exports_usd", "reserves_usd"]], on="country_id", how="left")
    total = out["total_debt_usd"].sum()
    out["total_debt_billion"] = out["total_debt_usd"] / 1e9
    out["external_debt_stock_billion"] = out["external_debt_stock_usd"] / 1e9
    out["pct_of_global"] = out["total_debt_usd"] / total * 100
    out["debt_to_gni_pct"] = out["external_debt_stock_usd"] / out["gni_usd"] * 100
    out["debt_to_exports_pct"] = out["external_debt_stock_usd"] / out["exports_usd"] * 100
    out["reserves_to_debt_pct"] = out["reserves_usd"] / out["external_debt_stock_usd"] * 100
    out["debt_category"] = categorize(out["total_debt_usd"])
    out = out.sort_values("total_debt_usd", ascending=False).reset_index(drop=True)
    out["debt_rank"] = range(1, len(out) + 1)
    out["cumulative_pct"] = out["pct_of_global"].cumsum()
    return out


def indicator_summary(df: pd.DataFrame) -> pd.DataFrame:
    out = df.groupby(["indicator_code", "indicator_name", "indicator_group"], as_index=False).agg(
        total_debt_usd=("debt_usd", "sum"), countries=("country_id", "nunique"),
        mean_usd=("debt_usd", "mean"), median_usd=("debt_usd", "median"))
    out["total_debt_billion"] = out["total_debt_usd"] / 1e9
    out["pct_of_global"] = out["total_debt_usd"] / out["total_debt_usd"].sum() * 100
    return out.sort_values("total_debt_usd", ascending=False).reset_index(drop=True)


def group_summary(df: pd.DataFrame) -> pd.DataFrame:
    out = df.groupby("indicator_group", as_index=False).agg(
        total_debt_usd=("debt_usd", "sum"), indicators=("indicator_id", "nunique"), records=("debt_id", "count"))
    out["total_debt_billion"] = out["total_debt_usd"] / 1e9
    out["pct_of_global"] = out["total_debt_usd"] / out["total_debt_usd"].sum() * 100
    return out.sort_values("total_debt_usd", ascending=False).reset_index(drop=True)


def segment_summary(cs: pd.DataFrame, by: str) -> pd.DataFrame:
    out = cs.groupby(by, as_index=False).agg(
        countries=("country_id", "count"),
        external_debt_stock_billion=("external_debt_stock_billion", "sum"),
        gni_billion=("gni_usd", lambda s: s.sum() / 1e9),
        median_debt_to_gni_pct=("debt_to_gni_pct", "median"))
    out["debt_to_gni_pct"] = out["external_debt_stock_billion"] / out["gni_billion"] * 100
    return out.sort_values("external_debt_stock_billion", ascending=False).reset_index(drop=True)


def statistics(df: pd.DataFrame, cs: pd.DataFrame) -> dict:
    v = df["debt_usd"]
    t = cs["total_debt_usd"]
    return {
        "record_mean_usd": float(v.mean()), "record_median_usd": float(v.median()),
        "record_std_usd": float(v.std()), "record_min_usd": float(v.min()), "record_max_usd": float(v.max()),
        "record_skew": float(v.skew()),
        "country_total_mean_usd": float(t.mean()), "country_total_median_usd": float(t.median()),
        "country_total_q25_usd": float(t.quantile(0.25)), "country_total_q75_usd": float(t.quantile(0.75)),
        "countries_above_mean": int((t > t.mean()).sum()),
    }


def correlations(cs: pd.DataFrame) -> pd.DataFrame:
    cols = {"external_debt_stock_billion": "Ext. debt stock", "gni_usd": "GNI", "exports_usd": "Exports",
            "reserves_usd": "Reserves", "total_debt_billion": "Total (all indicators)"}
    return cs[list(cols)].rename(columns=cols).corr(method="spearman").round(3)


def findings(cs: pd.DataFrame, ind: pd.DataFrame, grp: pd.DataFrame, region: pd.DataFrame,
             income: pd.DataFrame) -> dict:
    """Headline numbers used in the reports and the app's Insights page."""
    top5 = cs.head(5)
    n80 = int((cs["cumulative_pct"] < 80).sum()) + 1
    ratio = cs.dropna(subset=["debt_to_gni_pct"]).sort_values("debt_to_gni_pct", ascending=False)
    return {
        "countries": int(len(cs)),
        "indicators": int(len(ind)),
        "total_debt_trillion": float(cs["total_debt_usd"].sum() / 1e12),
        "external_debt_stock_trillion": float(cs["external_debt_stock_usd"].sum() / 1e12),
        "top_country": cs.iloc[0]["country_name"],
        "top_country_pct": float(cs.iloc[0]["pct_of_global"]),
        "top5_countries": top5["country_name"].tolist(),
        "top5_pct": float(top5["pct_of_global"].sum()),
        "countries_for_80pct": n80,
        "lowest_country": cs.iloc[-1]["country_name"],
        "lowest_country_billion": float(cs.iloc[-1]["total_debt_billion"]),
        "top_indicator": ind.iloc[0]["indicator_name"],
        "top_indicator_pct": float(ind.iloc[0]["pct_of_global"]),
        "top_group": grp.iloc[0]["indicator_group"],
        "top_group_pct": float(grp.iloc[0]["pct_of_global"]),
        "category_counts": cs["debt_category"].value_counts().to_dict(),
        "highest_debt_to_gni": ratio.head(5)[["country_name", "debt_to_gni_pct"]].round(1).values.tolist(),
        "median_debt_to_gni": float(ratio["debt_to_gni_pct"].median()),
        "countries_debt_over_gni_60": int((ratio["debt_to_gni_pct"] > 60).sum()),
        "top_region": region.iloc[0]["region"],
        "top_region_billion": float(region.iloc[0]["external_debt_stock_billion"]),
        "highest_ratio_income_group": income.sort_values("median_debt_to_gni_pct", ascending=False).iloc[0]["income_group"],
    }
