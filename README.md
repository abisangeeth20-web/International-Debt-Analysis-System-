# International Debt Analysis System (Python, SQL, Power BI & Streamlit)

An end-to-end analytics pipeline on the **World Bank International Debt Statistics** dataset:
CSV → pandas → cleaning → normalised **MySQL** database (primary / foreign keys) → **30 SQL queries**
→ EDA with **Matplotlib / Seaborn / Plotly** → interactive **Streamlit** app and **Power BI** dashboard
→ insights and recommendations.

**Live app:** https://intl-debt-analysis-system.streamlit.app/

## Results at a glance

| | |
|---|---|
| Countries / debt indicators / records | 120 / 441 / 26,966 |
| Total debt (sum of all debt indicators) | $93.80T |
| External debt stock (no double counting) | $8.68T |
| Largest borrower | China: 21.5% of the total, $2,530B external debt stock |
| Concentration | the top 5 hold 48.1%; 22 countries reach 80% |
| Least indebted | Tonga ($2.75B) |
| Heaviest burden (debt / GNI) | Mozambique 380%, Lebanon 333%, Mongolia 217% |
| Debt categories | 30 High, 59 Medium, 31 Low |

The full write-ups are in [reports/EDA_Report.md](reports/EDA_Report.md) and
[reports/Insights_Report.md](reports/Insights_Report.md).

### A data-quality fix worth knowing
The raw file mixes five **macro-economic indicators** (GNI, exports, imports, reserves, current account)
in with the debt indicators. Summing them as "debt" added **$61.7T** and made GNI the "largest debt
indicator". The cleaning step moves them to a separate `country_macro` table and uses them for
debt-to-GNI ratios instead.

## Project structure

```
├── app.py                       Streamlit app (9 pages)
├── run_pipeline.py              runs the whole pipeline end to end
├── src/
│   ├── config.py                paths, thresholds, indicator groups, DB settings
│   ├── preprocessing.py         CSV → DataFrame, profiling, cleaning, normalisation
│   ├── database.py              SQLite + MySQL schema/load (PK/FK), query helpers
│   ├── sql_runner.py            parses and runs the 30 queries
│   ├── eda.py                   summaries, statistics, findings
│   ├── plotting.py              Matplotlib / Seaborn / Plotly charts
│   └── powerbi_export.py        CSV extracts for Power BI
├── sql/
│   ├── 00_schema.sql            MySQL schema: tables, keys, views
│   ├── 01_basic_queries.sql     Q1-Q10
│   ├── 02_intermediate_queries.sql  Q11-Q20
│   └── 03_advanced_queries.sql  Q21-Q30
├── sql_outputs/                 result of every query (CSV, Excel, text report)
├── data/
│   ├── raw/                     international_debt.csv + World Bank IDS source files
│   └── processed/               cleaned CSVs + international_debt.db (SQLite copy)
├── notebooks/                   executed analysis notebook (+ build script)
├── reports/                     EDA report, insights report, documentation, figures, tables
├── International_Debt_Dashboard.pbix   Power BI dashboard (3 pages)
├── powerbi_data/                tables the .pbix reads
├── powerbi/build_pbix_pages.py  adds the report pages to the .pbix
└── POWERBI_GUIDE.md
```

## Database design

```
countries  (country_id PK, country_code UNIQUE, country_name, region, income_group, lending_category)
indicators (indicator_id PK, indicator_code UNIQUE, indicator_name, indicator_group)
debt_data  (debt_id PK, country_id FK→countries, indicator_id FK→indicators, debt_usd, debt_billion_usd,
            UNIQUE(country_id, indicator_id))
country_macro (country_id PK/FK→countries, gni_usd, exports_usd, imports_usd, reserves_usd, current_account_usd)
views: vw_top10_countries, vw_country_debt_profile
```

The design is normalised: names are stored once in the dimension tables, and the fact table holds only keys and values.
The same queries run on MySQL 8 and on the bundled SQLite copy, and the pipeline checks that both return
identical row counts.

## How to run

```bash
pip install -r requirements-dev.txt

python run_pipeline.py                 # SQLite only, no server needed
# or, with MySQL running:
set DEBT_DB_PASS=your_password         # PowerShell: $env:DEBT_DB_PASS="your_password"
python run_pipeline.py --mysql         # also creates + loads MySQL and runs the 30 queries there

streamlit run app.py
```

The app reads MySQL when `DEBT_DB_URL` is set (environment variable or `.streamlit/secrets.toml`),
for example `mysql+mysqlconnector://root:password@localhost:3306/international_debt`. Otherwise it uses
`data/processed/international_debt.db`. The deployed app uses that bundled copy.

## Streamlit app pages
**Overview** (KPIs, top 10, categories, treemap) · **Country Analysis** (drill-down, ratios, comparison) ·
**Indicator Analysis** (groups, top countries per indicator, heatmap) · **Debt Categories** (High / Medium /
Low, Pareto, >5% countries) · **Debt Burden** (debt/GNI by country, region and income group) ·
**SQL Query Results** (all 30 queries run live, with CSV download) · **Insights** (findings and
recommendations computed live) · **Power BI Dashboard** · **Data & Methodology**.
Sidebar filters: region and income group.

## Power BI
`International_Debt_Dashboard.pbix` has three pages: **Overview**, **Indicator Analysis** and **Insights**.
See [POWERBI_GUIDE.md](POWERBI_GUIDE.md) for refresh steps, the MySQL connection and DAX measures.

## Deliverables checklist (from the spec)

| Deliverable | Where |
|---|---|
| Raw CSV dataset | `data/raw/` |
| Cleaned dataset | `data/processed/international_debt_cleaned.csv` |
| MySQL schema with PK / FK | `sql/00_schema.sql` |
| Data inserted into SQL tables (Python → MySQL) | `src/database.py` (`build_mysql`) |
| 30 SQL analytical queries + results | `sql/`, `sql_outputs/` |
| Python processing & integration scripts | `src/`, `run_pipeline.py` |
| Visualizations (Matplotlib / Seaborn / Plotly) | `reports/figures/` |
| Interactive dashboards | `app.py` (Streamlit), `International_Debt_Dashboard.pbix` (Power BI) |
| EDA report with insights | `reports/EDA_Report.md`, `reports/Insights_Report.md` |
| Final documentation | `reports/Project_Documentation.md`, this README |

## Tech stack
Python 3.11+ (deployed on 3.13), pandas, NumPy, SQLAlchemy, mysql-connector-python, MySQL 8.4, SQLite, Matplotlib,
Seaborn, Plotly, Streamlit, Power BI Desktop, Jupyter.
