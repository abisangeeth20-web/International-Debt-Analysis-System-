# Power BI Dashboard Guide

File: **`International_Debt_Dashboard.pbix`** (open with Power BI Desktop, free)

## Report pages

| Page | Visuals |
|---|---|
| **Overview** | 4 KPI cards (total debt, countries, indicators, average debt), Top 10 countries bar (filtered to `debt_rank <= 10`), debt-category donut, country treemap, country slicer + table |
| **Indicator Analysis** | debt by indicator bar, countries-per-category donut, country drop-down slicer, country x indicator detail table |
| **Insights** | key findings and recommendations text, Top 10 countries by % of global debt |

## Data model

The report is built on the CSV extracts in `powerbi_data/`. `python run_pipeline.py` writes them from the
cleaned database.

| Table | Rows | Used for |
|---|---|---|
| `kpi_summary` | 1 | KPI cards |
| `country_debt_summary` | 120 | country bars, treemap, table, slicer |
| `indicator_debt_summary` | 441 | indicator bar |
| `debt_categories` | 3 | category donut |
| `country_indicator_matrix` | 26,966 | detail table + slicer |
| `countries`, `indicators`, `debt_data` | 120 / 441 / 26,966 | star schema (`debt_data` → `countries`, `indicators`) |

Extra extracts for further pages: `country_debt_profile.csv` (debt/GNI, region, income group),
`country_macro.csv`, `countries_enriched.csv`, `indicators_enriched.csv`, `indicator_group_summary.csv`.

## Refreshing after the pipeline runs

1. `python run_pipeline.py`
2. Open `International_Debt_Dashboard.pbix` → **Home → Refresh**
3. **File → Save**

The KPI card should then read **93.80** (trillion), not the old 155.50. The old figure included GNI,
exports, imports and reserves, which are not debt.

> If Power BI says a file was not found, the CSVs were moved. Go to **Transform data → Data source
> settings → Change Source** and point each file to this project's `powerbi_data/` folder.

## Connecting to MySQL instead of CSV (optional)

1. Load MySQL: set `DEBT_DB_PASS` (and `DEBT_DB_USER` / `DEBT_DB_HOST` if they differ), then
   `python run_pipeline.py --mysql`.
2. Power BI → **Get data → MySQL database** → server `localhost`, database `international_debt`.
   This needs the MySQL Connector/NET installed.
3. Select `countries`, `indicators`, `debt_data`, `country_macro` and the views `vw_top10_countries` and
   `vw_country_debt_profile`.
4. **Model view**: check the relationships `debt_data[country_id] → countries[country_id]`,
   `debt_data[indicator_id] → indicators[indicator_id]` and `country_macro[country_id] → countries[country_id]`.
5. Useful DAX measures:

```DAX
Total Debt (T) = DIVIDE(SUM(debt_data[debt_usd]), 1e12)
External Debt Stock (B) =
    DIVIDE(CALCULATE(SUM(debt_data[debt_usd]), indicators[indicator_code] = "DT.DOD.DECT.CD"), 1e9)
Debt to GNI % =
    DIVIDE(CALCULATE(SUM(debt_data[debt_usd]), indicators[indicator_code] = "DT.DOD.DECT.CD"),
           SUM(country_macro[gni_usd])) * 100
% of Global = DIVIDE(SUM(debt_data[debt_usd]), CALCULATE(SUM(debt_data[debt_usd]), ALL(countries))) * 100
```

## Sharing

- The `.pbix` is in the GitHub repo, and anyone with Power BI Desktop can open it.
- A PDF export (**File → Export → Export to PDF**) saved as `reports/powerbi/International_Debt_Dashboard.pdf`
  can be viewed in the browser on GitHub.
- PNG screenshots in `reports/powerbi/` are shown on the Streamlit app's **Power BI Dashboard** page.
- A public web link needs a Power BI Service account (**Publish → Publish to web**). Most organisations
  turn this off for student accounts.

## How the extra pages were added

`powerbi/build_pbix_pages.py` rewrites the report layout inside the `.pbix` (a zip file). It keeps the
original Overview page, fixes the Top-10 filter, and adds the two new pages using tables already in the model.
A backup of the original file is in `_old/` (not uploaded).
