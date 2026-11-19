# EDA Report: International Debt Analysis

Dataset: World Bank International Debt Statistics (IDS, 2022 release), `data/raw/international_debt.csv`.
All numbers come from `python run_pipeline.py` (`reports/pipeline_summary.json`, `reports/eda_tables/`).
Figures are in `reports/figures/`; the executed notebook is `notebooks/International_Debt_Analysis.ipynb`.

## 1. Data collection

| Item | Value |
|---|---|
| Raw shape | 27,445 rows x 5 columns |
| Columns | `country_name`, `country_code`, `indicator_name`, `indicator_code`, `debt_usd` |
| Data types | 4 text columns, `debt_usd` float64 |
| Countries / indicators | 120 / 446 |
| Missing values | 0 in every column |
| Exact duplicates / repeated (country, indicator) keys | 0 / 0 |
| Negative values | 0 |

Each row is one value (US$) for one country and one indicator.

## 2. Preprocessing

| Step | Result |
|---|---|
| Trim whitespace, upper-case codes, `debt_usd` → numeric | done |
| Rows with missing key or value | 0 dropped. Values are never imputed, because a debt figure cannot be invented. |
| Duplicates (exact and by country + indicator) | 0 removed |
| Negative values | 0 rejected |
| **Non-debt indicators moved out** | **479 rows**: GNI, exports, imports, total reserves, current account balance |
| Final debt table | **26,966 rows, 120 countries, 441 debt indicators** |
| Added attributes | region, income group, lending category (World Bank country metadata); `indicator_group` from the indicator code |

**Why the macro indicators were removed.** They are not borrowings. Together they add **$61.7T**
to the "debt" total; China's GNI alone is $18.2T, which would make GNI the "largest debt indicator".
They now live in the `country_macro` table and are used to compute debt-to-GNI, debt-to-exports and
reserves-to-debt ratios.

## 3. Statistical summary

| Measure | Single debt record | Country total |
|---|---|---|
| Mean | $3.48B | $781.6B |
| Median | $0.136B | $154.6B |
| 25th / 75th percentile | n/a | $39.7B / $588.5B |
| Max | $2,530B (China, external debt stock) | $20,164B (China) |
| Skewness | 40.8 | n/a |

Values are extremely right-skewed: the mean is about 25 times the median
(see `eda_07_value_distribution.png`, log scale). Medians and log scales are used throughout.

## 4. Country-wise debt distribution

**Total debt (spec definition = sum of all debt indicators): $93.80T. External debt stock (no double counting): $8.68T.**

Top 10 (`eda_01_top10_countries.png`):

| Rank | Country | Total debt | External debt stock | % of total |
|---|---|---|---|---|
| 1 | China | $20,164B | $2,530B | 21.50% |
| 2 | Brazil | $6,844B | $579B | 7.30% |
| 3 | Mexico | $6,588B | $586B | 7.02% |
| 4 | India | $6,247B | $616B | 6.66% |
| 5 | Indonesia | $5,288B | $396B | 5.64% |
| 6 | Turkiye | $4,376B | $456B | 4.67% |
| 7 | Argentina | $2,569B | $249B | 2.74% |
| 8 | Colombia | $2,385B | $184B | 2.54% |
| 9 | Egypt, Arab Rep. | $2,250B | $163B | 2.40% |
| 10 | Ukraine | $2,064B | $143B | 2.20% |

Lowest 10 (`eda_02_bottom10_countries.png`): Tonga ($2.75B), Sao Tome and Principe, Solomon Islands,
Samoa, Comoros, Timor-Leste, Vanuatu, Dominica, Central African Republic, Burundi. Together they hold
**0.07%** of the total.

**Concentration** (`eda_08_pareto_cumulative.png`): the top 5 countries hold **48.1%**, and
**22 of 120 countries** reach 80% of total debt. Only 22 countries are above the mean country total.

**Categories** (`eda_03_debt_categories.png`, thresholds = 75th / 25th percentile):

| Category | Rule | Countries | Share of total debt |
|---|---|---|---|
| High Debt | total ≥ $588B | 30 | 86.4% |
| Medium Debt | $40B to $588B | 59 | 12.9% |
| Low Debt | < $40B | 31 | 0.7% |

## 5. Indicators and their impact

By indicator group (`eda_04_indicator_groups.png`):

| Group | Indicators | Share of summed value |
|---|---|---|
| Debt Stocks | 67 | 70.3% |
| Debt Service | 57 | 8.1% |
| Disbursements | 56 | 7.0% |
| Principal Repayments | 56 | 6.3% |
| Net Flows | 61 | 2.2% |
| Interest Payments | 61 | 2.0% |
| Others (undisbursed, net transfers, commitments, arrears, rescheduling, relief) | 83 | 4.1% |

Top indicators (`eda_05_top_indicators.png`): External debt stocks total ($8,683B, 9.3%), long-term
($6,047B), variable rate ($3,675B), PPG ($3,382B), long-term public sector ($3,364B).

**Double counting.** Many indicators are sub-totals of others (total = long-term + short-term + IMF
credit; long-term = public + private). The heatmap (`eda_06_country_indicator_heatmap.png`) shows the
same amounts repeated across related indicators. The spec's "total debt" is therefore an index of scale,
not money owed. The external debt stock is the comparable figure.

## 6. Patterns, trends and relationships

- **Debt grows with economy size** (`eda_12_debt_vs_gni.png`, `eda_11_correlation.png`): the Spearman
  correlation of external debt stock is 0.90 with GNI, 0.90 with exports and 0.89 with reserves.
- **Burden is a different ranking from size** (`eda_09_debt_to_gni.png`): the highest debt-to-GNI ratios
  are Mozambique 380%, Lebanon 333%, Mongolia 217%, Montenegro 139% and Senegal 132%. China is only 14%.
  The median country is 45%; 39 countries are above 60% and 13 are above 100%.
- **Debt vs exports**: Mozambique (690%), Lebanon (506%), Senegal (447%), The Gambia (420%) and
  Bhutan (387%) would need years of export earnings to repay.
- **Thin reserve cover**: Sri Lanka (3%), Ethiopia (4%), Zimbabwe (4%), Mozambique (4%) and
  Pakistan (8%) hold reserves worth less than a tenth of their external debt.
- **Regions** (`eda_10_region_debt.png`): East Asia & Pacific holds the largest stock ($3,497B), then
  Latin America & Caribbean ($1,944B). Europe & Central Asia has the highest aggregate ratio (58% of GNI).
- **Income groups**: low-income countries owe 54% of their combined GNI, against 22% for upper-middle
  income. The poorest economies carry the heaviest relative load.

## 7. Comparisons (statistical)

| Segment | Countries | Ext. debt stock | Debt / GNI (aggregate) | Median debt / GNI |
|---|---|---|---|---|
| Upper middle income | 49 | $6,277B | 22.5% | 55.1% |
| Lower middle income | 46 | $2,177B | 30.0% | 46.7% |
| Low income | 23 | $197B | 54.2% | 40.1% |

The aggregate ratio for upper-middle income is pulled down by China; the median shows that the
typical upper-middle-income country is also heavily indebted.

## 8. Data quality notes

- The file holds one value per country and indicator (a single year), so there is no time series.
  "Trends" here means cross-sectional patterns.
- In the metadata, one country is "Not classified" and one is "High income". These two groups are too small to compare.
- Values as small as $0.10 exist (tiny arrears or relief items). They are valid and kept.
