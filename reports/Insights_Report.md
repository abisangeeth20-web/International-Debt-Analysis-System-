# Insights & Recommendations: International Debt Analysis

Numbers are from the cleaned data (120 countries, 441 debt indicators, 26,966 records).
They match the Streamlit **Insights** page and the Power BI **Insights** page.

## Country-wise debt distribution
- Total debt (sum of all debt indicators, the spec definition) is **$93.80T**. The external debt stock,
  the figure without double counting, is **$8.68T**.
- Debt is highly concentrated. **China holds 21.5%**, the top 5 (China, Brazil, Mexico, India,
  Indonesia) hold **48.1%**, and **22 of 120 countries** make up 80%.
- **30 High-debt countries hold 86.4%** of the total. The 31 Low-debt countries hold 0.7%.

## Highest and lowest debt
- Highest: **China** ($2,530B external debt stock), then India ($616B), Mexico ($586B), Brazil ($579B).
- Lowest: **Tonga** ($2.75B total), then Sao Tome and Principe, Solomon Islands, Samoa and Comoros.
  The bottom 10 together hold 0.07% of the total.

## Debt across indicators
- **Debt stocks are 70.3%** of the summed value, debt service 8.1%, disbursements 7.0%, principal
  repayments 6.3% and interest 2.0%.
- The largest single indicator is *External debt stocks, total*. The next four are its own sub-totals.
  This double counting means the summed "total debt" measures scale, not money owed.

## Trends and patterns
- External debt rises with economy size (Spearman 0.90 with GNI).
- **Size is not burden.** Relative to GNI, the most stretched countries are Mozambique (380%),
  Lebanon (333%), Mongolia (217%), Montenegro (139%) and Senegal (132%). China is 14%.
  **39 countries owe more than 60% of GNI** and 13 owe more than 100%.
- **Low-income countries owe 54% of their combined GNI**, against 22% for upper-middle income.
- Sri Lanka, Ethiopia, Zimbabwe, Mozambique and Pakistan have reserves covering less than 10% of
  their external debt.

## Recommendations (data-driven decision making)
1. **Rank risk by ratios** (debt/GNI, debt/exports, reserves/debt), not by totals. The highest-ratio
   countries need closer monitoring than the largest borrowers.
2. **Keep a concentration watch-list** of the top 5 borrowers. Together they move about half of the total.
3. **Target relief and concessional lending** at low-income, high-ratio countries (for example Mozambique
   and The Gambia).
4. **Use the external debt stock as the headline KPI.** Summing all indicators double-counts.
5. **Track debt service and interest** (cash leaving the country each year) together with stocks, to catch
   liquidity stress early, especially where reserves are thin.
6. **Add a time dimension next.** The file is a single snapshot. Loading the year columns of the World Bank
   IDS file (`data/raw/world_bank_ids/IDS_ALLCountries_Data.csv`) would show how debt is growing.
