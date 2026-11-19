# Project Documentation: International Debt Analysis System

**Domain:** Finance analytics and global economic data analysis
**Tools:** Python (pandas, NumPy, SQLAlchemy), MySQL 8.4 / SQLite, Matplotlib, Seaborn, Plotly, Streamlit, Power BI

## 1. Problem and objective
World Bank debt data arrives as a wide CSV of country × indicator values. Many indicators overlap, and
some are not debt at all. The objective is to take it through the full data lifecycle (collection,
cleaning, EDA, SQL storage, visualisation, insights) to support data-driven decisions about which
countries carry the most debt and the heaviest debt burden.

## 2. Data collection
- Source file: `data/raw/international_debt.csv` (27,445 rows, 5 columns, 120 countries, 446 indicators).
- World Bank IDS source and metadata files: `data/raw/world_bank_ids/`. The country metadata adds region,
  income group and lending category.
- `src/preprocessing.load_raw()` loads the CSV into a pandas DataFrame and checks the required columns.
  `profile()` records shape, dtypes, nulls, duplicates and negative values.

## 3. Preprocessing (`src/preprocessing.py`)
| Step | Rule | Effect |
|---|---|---|
| Standardise | trim spaces, collapse whitespace, upper-case codes | consistent keys |
| Type conversion | `debt_usd` → numeric (`errors="coerce"`) | bad values become NaN |
| Missing values | drop rows missing a key or value; never impute a money amount | 0 rows |
| Duplicates | exact duplicates, then duplicates on (country, indicator) | 0 rows |
| Validation | reject negative amounts | 0 rows |
| Relevant data only | move 5 macro indicators to `country_macro` | 479 rows moved |
| Enrichment | `indicator_group`, `debt_billion_usd`, region / income group | added |

Output: `data/processed/international_debt_cleaned.csv` (26,966 rows, 441 debt indicators).

## 4. Database design and SQL integration
- **Schema** (`sql/00_schema.sql`): `countries` and `indicators` are dimension tables with primary keys and
  unique business codes. `debt_data` is the fact table, with foreign keys to both and a unique
  (country, indicator) constraint. `country_macro` is a 1:1 extension of `countries`. There are two views:
  `vw_top10_countries` (used by Q25) and `vw_country_debt_profile`.
- **Normalisation:** country and indicator names are stored once. The fact table holds only keys and values.
- **Python → MySQL:** `src/database.build_mysql()` runs the DDL and inserts the rows in batches.
  `build_sqlite()` builds an identical SQLite copy, enforces foreign keys and runs `PRAGMA foreign_key_check`.
- **Performance:** there are indexes on the foreign keys and `indicator_group`. Queries aggregate on integer
  keys and join to dimensions only for labels.
- **30 queries** (`sql/01-03`): basic (SELECT / COUNT / WHERE), intermediate (GROUP BY, HAVING, subqueries,
  RANK) and advanced (PARTITION BY, running totals, CASE bucketing, views). Results are in `sql_outputs/`
  as one CSV per query, `all_query_results.xlsx` and `query_execution_report.txt`. The pipeline runs the
  queries on both engines and confirms identical row counts.

## 5. Exploratory data analysis
See `reports/EDA_Report.md`. It covers the country-wise distribution, highest and lowest countries,
indicator groups, statistical summaries (heavy right skew, skewness 40.8), concentration (Pareto),
relationships (Spearman correlation with GNI, exports and reserves), and comparisons by region and
income group.

## 6. Visualisation
- **Static** (`reports/figures/eda_*.png`, Matplotlib / Seaborn): top and bottom 10, categories, indicator
  groups, top indicators, heatmap, value distribution, Pareto curve, debt/GNI, regions, correlation, scatter.
- **Interactive** (`reports/figures/interactive/*.html`, Plotly): treemap, scatter, top 20.
- **Streamlit app** (`app.py`, 9 pages, region / income filters). It is connected to MySQL when
  `DEBT_DB_URL` is set, otherwise to the bundled SQLite database.
- **Power BI** (`International_Debt_Dashboard.pbix`): Overview, Indicator Analysis and Insights pages.

## 7. Insights and reporting
See `reports/Insights_Report.md` and the **Insights** page of the app, where the numbers are computed live.
The main messages:
1. Debt is concentrated: China holds 21.5% and 22 countries hold 80%.
2. Size and burden are different rankings: Mozambique, Lebanon and Mongolia owe 2-4x their GNI.
3. Low-income countries owe 54% of GNI, against 22% for upper-middle income.
4. Summing all indicators double-counts; the external debt stock ($8.68T) is the reliable headline.

## 8. Key design decisions
| Decision | Reason |
|---|---|
| Drop, never impute, missing debt values | an invented debt amount would be misleading |
| Separate macro indicators | they are not debt, and including them added $61.7T |
| Keep the spec's "sum of indicators" total, and report external debt stock next to it | answers the spec questions while showing the real money owed |
| Category thresholds = 75th / 25th percentile ($588B / $40B) | data-driven, reproducible, and checked by the pipeline |
| SQLite copy of the MySQL database | the cloud app works without a database server |
| Credentials only from environment variables | no passwords in the repository |

## 9. Reproducing
```bash
pip install -r requirements-dev.txt
python run_pipeline.py --mysql      # or without --mysql for SQLite only
python notebooks/build_notebook.py
python -m nbconvert --to notebook --execute --inplace notebooks/International_Debt_Analysis.ipynb
streamlit run app.py
```

## 10. Limitations and next steps
- The dataset is a single snapshot, so there are no year-on-year trends. The IDS source file has year
  columns 2000-2032 that could add a time dimension.
- Counterpart (creditor) detail is not used. Adding it would show who the debt is owed to.
