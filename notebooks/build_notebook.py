"""Build notebooks/International_Debt_Analysis.ipynb from the src/ modules.

Run:  python notebooks/build_notebook.py
      python -m nbconvert --to notebook --execute --inplace notebooks/International_Debt_Analysis.ipynb
"""
from pathlib import Path

import nbformat as nbf

nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
    md("# International Debt Analysis System\n"
       "**Python · SQL · Visualization** - World Bank International Debt Statistics\n\n"
       "This notebook walks through the full data lifecycle required by the project spec:\n"
       "1. Data collection (CSV → DataFrame)\n2. Data preprocessing\n3. Exploratory data analysis\n"
       "4. Database design & SQL integration (30 queries)\n5. Data visualization\n6. Insights & reporting\n\n"
       "The logic lives in `src/` so the notebook, `run_pipeline.py` and the Streamlit app all share it."),
    code("import os, sys, json\n"
         "from pathlib import Path\n"
         "ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\n"
         "os.chdir(ROOT); sys.path.insert(0, str(ROOT))\n"
         "import pandas as pd, numpy as np\n"
         "import matplotlib.pyplot as plt, seaborn as sns\n"
         "from IPython.display import Image, display\n"
         "from src import config, preprocessing, database, sql_runner, eda, plotting\n"
         "pd.set_option('display.max_colwidth', 70); pd.set_option('display.float_format', '{:,.4f}'.format)"),
    md("## 1. Data collection\nLoad the raw CSV into a pandas DataFrame and inspect structure, columns and data types."),
    code("raw = preprocessing.load_raw()\nprint(raw.shape)\nraw.head()"),
    code("raw.info()"),
    code("prof = preprocessing.profile(raw)\n{k: v for k, v in prof.items() if k not in ('columns', 'dtypes')}"),
    code("raw['debt_usd'].describe()"),
    md("### The raw file mixes non-debt indicators in\nFive indicators are macro-economic, not debt. "
       "GNI alone dwarfs every debt figure, so leaving them in would distort every total."),
    code("macro_mask = raw['indicator_code'].isin(config.MACRO_INDICATORS)\n"
         "raw[macro_mask].groupby('indicator_name')['debt_usd'].sum().div(1e12).rename('total_trillion_usd')"),
    md("## 2. Data preprocessing\nWhitespace and code standardisation, numeric conversion, missing values (dropped, "
       "never invented), duplicate removal, validation, and moving the macro indicators to their own table."),
    code("debt_df, macro_df, log = preprocessing.clean(raw)\nlog"),
    code("debt_df.isna().sum()"),
    code("debt_df.head()"),
    code("macro_df.head()"),
    md("### Normalised tables\nAdd region / income group from the World Bank country metadata and build "
       "the dimension and fact tables."),
    code("meta = preprocessing.load_country_metadata()\n"
         "countries, indicators, fact, macro = preprocessing.build_dimensions(debt_df, macro_df, meta)\n"
         "tables = {'countries': countries, 'indicators': indicators, 'debt_data': fact, 'country_macro': macro}\n"
         "{k: v.shape for k, v in tables.items()}"),
    code("countries.head()"),
    code("indicators['indicator_group'].value_counts()"),
    md("## 3. Database design & SQL integration\n"
       "Star schema: `countries` and `indicators` (dimensions, primary keys) ← `debt_data` (fact, foreign keys), "
       "plus `country_macro` (1:1 with countries). The MySQL DDL is in `sql/00_schema.sql`; "
       "`python run_pipeline.py --mysql` loads MySQL. The notebook uses the identical SQLite copy."),
    code("print((config.SQL_DIR / '00_schema.sql').read_text()[:1800])"),
    code("counts = database.build_sqlite(tables)\ncounts"),
    code("database.sqlite_query('PRAGMA foreign_key_list(debt_data)')"),
    md("### The 30 analytical queries"),
    code("bank = sql_runner.load_query_bank()\n"
         "for q in bank:\n"
         "    res = database.sqlite_query(q['sql'])\n"
         "    print(f\"\\n{q['id']} [{q['category']}] {q['title']}  ->  {len(res)} rows\")\n"
         "    print(res.head(5).to_string(index=False))"),
    md("## 4. Exploratory data analysis"),
    code("df = eda.full_frame(tables)\n"
         "cs = eda.country_summary(df, macro)\nind = eda.indicator_summary(df)\ngrp = eda.group_summary(df)\n"
         "region = eda.segment_summary(cs, 'region')\nincome = eda.segment_summary(cs, 'income_group')\n"
         "corr = eda.correlations(cs)\nstats = eda.statistics(df, cs)\n"
         "{k: round(v / 1e9, 3) if k.endswith('usd') else round(v, 3) for k, v in stats.items()}"),
    md("### Country-wise debt distribution - highest and lowest"),
    code("cs[['debt_rank','country_name','total_debt_billion','external_debt_stock_billion','pct_of_global','debt_category']].head(10)"),
    code("cs[['debt_rank','country_name','total_debt_billion','pct_of_global']].tail(10)"),
    md("### Indicators and indicator groups"),
    code("ind[['indicator_name','indicator_group','total_debt_billion','pct_of_global']].head(10)"),
    code("grp"),
    md("### Debt burden: region, income group and debt-to-GNI"),
    code("region"), code("income"),
    code("cs.dropna(subset=['debt_to_gni_pct']).nlargest(10, 'debt_to_gni_pct')[['country_name','income_group','external_debt_stock_billion','debt_to_gni_pct']]"),
    md("### Relationships"), code("corr"),
    md("## 5. Visualizations (Matplotlib / Seaborn / Plotly)"),
    code("figs = plotting.make_all(df, cs, ind, grp, region, corr)\n"
         "for f in figs:\n    if f.endswith('.png'):\n        display(Image(filename=str(config.FIGURES_DIR / f), width=850))"),
    md("## 6. Insights"),
    code("f = eda.findings(cs, ind, grp, region, income)\njson.loads(json.dumps(f, default=str))"),
    md("**Summary**\n"
       "- Debt is concentrated: China alone is about a fifth of the total, the top 5 about half, and ~22 of 120 "
       "countries make up 80%.\n"
       "- Debt-stock indicators dominate the summed value; summing all indicators double-counts, so the external "
       "debt stock is the better headline figure.\n"
       "- The largest borrowers are not the most stretched: relative to GNI, Mozambique, Lebanon and Mongolia "
       "carry the heaviest load, and low-income countries owe the most relative to their economies.\n\n"
       "See `reports/EDA_Report.md` and `reports/Insights_Report.md` for the full write-up."),
]
nb["cells"] = cells
nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
out = Path(__file__).with_name("International_Debt_Analysis.ipynb")
nbf.write(nb, out)
print("wrote", out)
