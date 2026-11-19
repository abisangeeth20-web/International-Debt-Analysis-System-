"""Central configuration: paths, constants, database settings."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── Data paths ────────────────────────────────────────────────
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_CSV = RAW_DIR / "international_debt.csv"
COUNTRY_META_CSV = RAW_DIR / "world_bank_ids" / "IDS_CountryMetaData.csv"

CLEANED_CSV = PROCESSED_DIR / "international_debt_cleaned.csv"
MACRO_CSV = PROCESSED_DIR / "country_macro.csv"
COUNTRIES_CSV = PROCESSED_DIR / "countries.csv"
INDICATORS_CSV = PROCESSED_DIR / "indicators.csv"
SQLITE_DB = PROCESSED_DIR / "international_debt.db"

SQL_DIR = ROOT / "sql"
SQL_OUTPUT_DIR = ROOT / "sql_outputs"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
EDA_TABLES_DIR = REPORTS_DIR / "eda_tables"
POWERBI_DATA_DIR = ROOT / "powerbi_data"

SQL_QUERY_FILES = [
    ("Basic", SQL_DIR / "01_basic_queries.sql"),
    ("Intermediate", SQL_DIR / "02_intermediate_queries.sql"),
    ("Advanced", SQL_DIR / "03_advanced_queries.sql"),
]

# ── Indicators that are NOT debt ──────────────────────────────
# The raw file mixes five macro-economic indicators in with the debt
# indicators. They are not borrowings, so adding them to "total debt"
# would inflate it (China's GNI alone is $18.2T). They are moved to a
# separate `country_macro` table and used for debt-to-GNI ratios.
MACRO_INDICATORS = {
    "NY.GNP.MKTP.CD": "gni_usd",
    "BX.GSR.TOTL.CD": "exports_usd",
    "BM.GSR.TOTL.CD": "imports_usd",
    "FI.RES.TOTL.CD": "reserves_usd",
    "BN.CAB.XOKA.CD": "current_account_usd",
}

# Headline "true" external debt figure per country.
TOTAL_EXTERNAL_DEBT_CODE = "DT.DOD.DECT.CD"

# Indicator families, keyed by the 2nd segment of the World Bank code.
INDICATOR_GROUPS = {
    "DOD": "Debt Stocks",
    "TDS": "Debt Service",
    "INT": "Interest Payments",
    "AMT": "Principal Repayments",
    "DIS": "Disbursements",
    "NFL": "Net Flows",
    "NTR": "Net Transfers",
    "COM": "Commitments",
    "UND": "Undisbursed Debt",
    "AXA": "Arrears",
    "IXA": "Arrears",
    "AXF": "Debt Relief",
    "IXF": "Debt Relief",
    "AXR": "Debt Rescheduling",
    "IXR": "Debt Rescheduling",
    "DXR": "Debt Rescheduling",
    "TXR": "Debt Rescheduling",
    "DSB": "Debt Relief",
    "DSF": "Debt Relief",
}
INDICATOR_GROUP_OVERRIDES = {"DT.DOD.MDRI.CD": "Debt Relief"}

# ── Debt category thresholds (total debt per country, USD) ────
# 75th / 25th percentile of total country debt in the cleaned data.
# run_pipeline.py re-computes the percentiles and warns if they drift.
HIGH_DEBT_THRESHOLD = 588_000_000_000
LOW_DEBT_THRESHOLD = 40_000_000_000

# ── MySQL (optional, used locally and by Power BI) ────────────
# Credentials come from environment variables, never from the repo.
MYSQL = {
    "host": os.environ.get("DEBT_DB_HOST", "localhost"),
    "port": int(os.environ.get("DEBT_DB_PORT", "3306")),
    "user": os.environ.get("DEBT_DB_USER", "root"),
    "password": os.environ.get("DEBT_DB_PASS", ""),
    "database": os.environ.get("DEBT_DB_NAME", "international_debt"),
}

RANDOM_STATE = 42
