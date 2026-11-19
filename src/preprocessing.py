"""Data collection (CSV -> DataFrame), profiling and cleaning."""
from __future__ import annotations

import pandas as pd

from . import config

REQUIRED_COLUMNS = ["country_name", "country_code", "indicator_name", "indicator_code", "debt_usd"]


# ── 1. Data collection ────────────────────────────────────────
def load_raw(path=config.RAW_CSV) -> pd.DataFrame:
    """Read the raw CSV into a DataFrame and check the expected columns exist."""
    df = pd.read_csv(path)
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Raw file is missing columns: {sorted(missing)}")
    return df


def profile(df: pd.DataFrame) -> dict:
    """Structure, dtypes and quality numbers for the report."""
    return {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "null_counts": {c: int(n) for c, n in df.isna().sum().items()},
        "exact_duplicates": int(df.duplicated().sum()),
        "key_duplicates": int(df.duplicated(["country_code", "indicator_code"]).sum()),
        "unique_countries": int(df["country_code"].nunique()),
        "unique_indicators": int(df["indicator_code"].nunique()),
        "negative_values": int((pd.to_numeric(df["debt_usd"], errors="coerce") < 0).sum()),
        "zero_values": int((pd.to_numeric(df["debt_usd"], errors="coerce") == 0).sum()),
    }


# ── 2. Cleaning ───────────────────────────────────────────────
def indicator_group(code: str) -> str:
    if code in config.INDICATOR_GROUP_OVERRIDES:
        return config.INDICATOR_GROUP_OVERRIDES[code]
    if code in config.MACRO_INDICATORS:
        return "Macro-economic"
    parts = code.split(".")
    return config.INDICATOR_GROUPS.get(parts[1] if len(parts) > 1 else "", "Other")


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Clean the raw data.

    Returns (debt_df, macro_df, log):
      debt_df  - long table, one row per (country, debt indicator)
      macro_df - wide table, one row per country with GNI / exports / ...
      log      - counts of everything that was changed, for the report
    """
    log = {"rows_in": int(len(df))}
    df = df[REQUIRED_COLUMNS].copy()

    # Standardise text columns
    for col in ["country_name", "indicator_name", "indicator_code"]:
        df[col] = df[col].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    df["country_code"] = df["country_code"].astype("string").str.strip().str.upper()
    df["indicator_code"] = df["indicator_code"].str.upper()

    # Type conversion: debt value must be numeric
    df["debt_usd"] = pd.to_numeric(df["debt_usd"], errors="coerce").astype("float64")

    # Missing values. A debt figure cannot be invented, so rows without a
    # value (or without a country / indicator key) are dropped, not imputed.
    key_null = df[["country_code", "indicator_code"]].isna().any(axis=1)
    log["rows_missing_key_dropped"] = int(key_null.sum())
    df = df[~key_null]
    value_null = df["debt_usd"].isna()
    log["rows_missing_value_dropped"] = int(value_null.sum())
    df = df[~value_null]

    # Fill a missing name from the same code if any other row has it
    for name_col, code_col in [("country_name", "country_code"), ("indicator_name", "indicator_code")]:
        lookup = df.dropna(subset=[name_col]).drop_duplicates(code_col).set_index(code_col)[name_col]
        df[name_col] = df[name_col].fillna(df[code_col].map(lookup))

    # Duplicates: exact copies, then repeated (country, indicator) keys
    log["exact_duplicates_removed"] = int(df.duplicated().sum())
    df = df.drop_duplicates()
    log["key_duplicates_removed"] = int(df.duplicated(["country_code", "indicator_code"]).sum())
    df = df.drop_duplicates(["country_code", "indicator_code"], keep="first")

    # Validation: debt amounts in this file are all positive gross amounts
    log["negative_values_dropped"] = int((df["debt_usd"] < 0).sum())
    df = df[df["debt_usd"] >= 0]

    # Filter relevant data: split macro-economic (non-debt) indicators out
    is_macro = df["indicator_code"].isin(config.MACRO_INDICATORS.keys())
    log["macro_rows_moved"] = int(is_macro.sum())
    macro_long = df[is_macro]
    macro_df = (
        macro_long.pivot_table(index="country_code", columns="indicator_code", values="debt_usd", aggfunc="first")
        .rename(columns=config.MACRO_INDICATORS)
        .reindex(columns=list(config.MACRO_INDICATORS.values()))
        .reset_index()
    )
    debt_df = df[~is_macro].copy()

    # Derived columns
    debt_df["indicator_group"] = debt_df["indicator_code"].map(indicator_group)
    debt_df["debt_billion_usd"] = (debt_df["debt_usd"] / 1e9).round(6)
    debt_df = debt_df.sort_values(["country_name", "indicator_code"]).reset_index(drop=True)

    log["rows_out"] = int(len(debt_df))
    log["countries_out"] = int(debt_df["country_code"].nunique())
    log["indicators_out"] = int(debt_df["indicator_code"].nunique())
    return debt_df, macro_df, log


def load_country_metadata(path=config.COUNTRY_META_CSV) -> pd.DataFrame:
    """Region / income group / lending category from the World Bank metadata file."""
    meta = pd.read_csv(path, encoding="latin-1")
    meta = meta.rename(columns={
        "Code": "country_code", "Region": "region",
        "Income Group": "income_group", "Lending category": "lending_category",
    })[["country_code", "region", "income_group", "lending_category"]]
    meta["country_code"] = meta["country_code"].str.strip().str.upper()
    for c in ["region", "income_group", "lending_category"]:
        meta[c] = meta[c].fillna("Not classified").str.strip()
    return meta


def build_dimensions(debt_df: pd.DataFrame, macro_df: pd.DataFrame, meta: pd.DataFrame):
    """Normalise into countries / indicators / debt_data / country_macro tables."""
    countries = (
        debt_df[["country_code", "country_name"]].drop_duplicates("country_code")
        .sort_values("country_name").reset_index(drop=True)
    )
    countries.insert(0, "country_id", range(1, len(countries) + 1))
    countries = countries.merge(meta, on="country_code", how="left")
    for c in ["region", "income_group", "lending_category"]:
        countries[c] = countries[c].fillna("Not classified")

    indicators = (
        debt_df[["indicator_code", "indicator_name", "indicator_group"]].drop_duplicates("indicator_code")
        .sort_values("indicator_code").reset_index(drop=True)
    )
    indicators.insert(0, "indicator_id", range(1, len(indicators) + 1))

    fact = (
        debt_df.merge(countries[["country_id", "country_code"]], on="country_code")
        .merge(indicators[["indicator_id", "indicator_code"]], on="indicator_code")
    )
    fact = fact[["country_id", "indicator_id", "debt_usd", "debt_billion_usd"]].sort_values(
        ["country_id", "indicator_id"]).reset_index(drop=True)
    fact.insert(0, "debt_id", range(1, len(fact) + 1))

    macro = macro_df.merge(countries[["country_id", "country_code"]], on="country_code", how="inner")
    macro = macro[["country_id"] + list(config.MACRO_INDICATORS.values())].sort_values("country_id")

    return countries, indicators, fact, macro
