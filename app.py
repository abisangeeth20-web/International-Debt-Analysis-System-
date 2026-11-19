"""
International Debt Analysis System - Streamlit dashboard.

Data source:
  * MySQL, when a connection URL is configured (env var DEBT_DB_URL or
    st.secrets["DEBT_DB_URL"], e.g. mysql+mysqlconnector://user:pass@host:3306/international_debt)
  * otherwise the bundled SQLite copy data/processed/international_debt.db
    (same schema, same data - this is what the Streamlit Cloud app uses).

Run locally:  streamlit run app.py
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text

from src import config, eda
from src.sql_runner import load_query_bank

st.set_page_config(page_title="International Debt Analysis", page_icon="🌍", layout="wide")

ROOT = Path(__file__).resolve().parent
BLUE = "#2a78d6"
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]
CATEGORICAL = ["#2a78d6", "#008300", "#e87ba4", "#eda100", "#1baf7a", "#eb6834", "#4a3aa7", "#e34948"]
CAT_COLOR = {"High Debt": "#d03b3b", "Medium Debt": "#fab219", "Low Debt": "#0ca30c"}
CAT_ORDER = ["High Debt", "Medium Debt", "Low Debt"]
TEMPLATE = "plotly_white"


# ══════════════════════════════════════════════════════════════
# DATA ACCESS
# ══════════════════════════════════════════════════════════════
def _db_url() -> tuple[str, str]:
    url = os.environ.get("DEBT_DB_URL")
    if not url:
        try:
            url = st.secrets.get("DEBT_DB_URL")
        except Exception:
            url = None
    if url:
        return url, "MySQL"
    return f"sqlite:///{(ROOT / 'data' / 'processed' / 'international_debt.db').as_posix()}", "SQLite (bundled)"


@st.cache_resource
def get_engine():
    url, label = _db_url()
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return engine, label
    except Exception:
        if label == "MySQL":  # fall back to the bundled copy
            sqlite_url = f"sqlite:///{(ROOT / 'data' / 'processed' / 'international_debt.db').as_posix()}"
            return create_engine(sqlite_url), "SQLite (MySQL unreachable)"
        raise


@st.cache_data(ttl=3600, show_spinner=False)
def run_query(sql: str) -> pd.DataFrame:
    engine, _ = get_engine()
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn)


@st.cache_data(ttl=3600, show_spinner="Loading data from the database...")
def load_frames():
    df = run_query("""
        SELECT d.debt_id, d.country_id, d.indicator_id, d.debt_usd, d.debt_billion_usd,
               c.country_name, c.country_code, c.region, c.income_group, c.lending_category,
               i.indicator_code, i.indicator_name, i.indicator_group
        FROM debt_data d
        JOIN countries  c ON d.country_id   = c.country_id
        JOIN indicators i ON d.indicator_id = i.indicator_id
    """)
    macro = run_query("SELECT * FROM country_macro")
    cs = eda.country_summary(df, macro)
    ind = eda.indicator_summary(df)
    grp = eda.group_summary(df)
    return df, macro, cs, ind, grp


def short(s: str, n: int = 55) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def hbar(data, x, y, xlabel, color=BLUE, fmt="$%{x:,.1f}B", height=None):
    fig = px.bar(data.iloc[::-1], x=x, y=y, orientation="h", template=TEMPLATE,
                 color_discrete_sequence=[color], labels={x: xlabel, y: ""})
    fig.update_traces(hovertemplate="%{y}<br>" + fmt + "<extra></extra>", marker_line_width=0)
    fig.update_layout(height=height or max(260, 34 * len(data) + 80), margin=dict(l=0, r=10, t=10, b=0))
    return fig


try:
    df, macro, cs_all, ind_all, grp_all = load_frames()
    _, DB_LABEL = get_engine()
except Exception as e:  # pragma: no cover - shown in the UI
    st.error(f"Could not load the database: {e}")
    st.stop()


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
st.sidebar.title("🌍 International Debt")
st.sidebar.caption(f"Data source: **{DB_LABEL}**")
PAGES = ["Overview", "Country Analysis", "Indicator Analysis", "Debt Categories", "Debt Burden (vs GNI)",
         "SQL Query Results", "Insights", "Power BI Dashboard", "Data & Methodology"]
page = st.sidebar.radio("Navigate", PAGES)

st.sidebar.divider()
st.sidebar.subheader("Filters")
regions = sorted(cs_all["region"].unique())
incomes = sorted(cs_all["income_group"].unique())
sel_regions = st.sidebar.multiselect("Region", regions, placeholder="All regions")
sel_incomes = st.sidebar.multiselect("Income group", incomes, placeholder="All income groups")
st.sidebar.caption("Filters apply to Overview, Debt Categories and Debt Burden.")


def filtered_cs() -> pd.DataFrame:
    cs = cs_all
    if sel_regions:
        cs = cs[cs["region"].isin(sel_regions)]
    if sel_incomes:
        cs = cs[cs["income_group"].isin(sel_incomes)]
    return cs


st.sidebar.divider()
st.sidebar.caption("World Bank International Debt Statistics (IDS 2022 release)")
st.sidebar.caption(f"{len(cs_all)} countries · {len(ind_all)} debt indicators · {len(df):,} records")


# ══════════════════════════════════════════════════════════════
# 1. OVERVIEW
# ══════════════════════════════════════════════════════════════
if page == "Overview":
    st.title("International Debt Analysis")
    st.caption("Country-wise and indicator-wise view of the World Bank International Debt Statistics.")
    cs = filtered_cs()
    if cs.empty:
        st.warning("No countries match the selected filters.")
        st.stop()
    sub = df[df["country_id"].isin(cs["country_id"])]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Countries", f"{len(cs)}")
    c2.metric("Debt indicators", f"{sub['indicator_id'].nunique()}")
    c3.metric("Records", f"{len(sub):,}")
    c4.metric("Total debt (all indicators)", f"${cs['total_debt_usd'].sum() / 1e12:,.2f}T")
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("External debt stock", f"${cs['external_debt_stock_usd'].sum() / 1e12:,.2f}T",
              help="Sum of 'External debt stocks, total (DOD)' - the headline debt figure without double counting.")
    c6.metric("Largest country", cs.iloc[0]["country_name"], f"{cs.iloc[0]['pct_of_global']:.1f}% of total",
              delta_color="off")
    c7.metric("Median debt / GNI", f"{cs['debt_to_gni_pct'].median():.1f}%")
    c8.metric("Avg debt record", f"${sub['debt_usd'].mean() / 1e9:,.2f}B")
    st.caption("“Total debt” follows the project spec: the sum of every debt indicator. Several indicators "
               "overlap (total = long-term + short-term + IMF credit), so for comparing countries the "
               "**external debt stock** is the cleaner measure.")

    st.divider()
    left, right = st.columns([3, 2])
    with left:
        st.subheader("Top 10 countries by total debt")
        st.plotly_chart(hbar(cs.head(10), "total_debt_billion", "country_name", "Total debt (billion USD)"),
                        width="stretch")
    with right:
        st.subheader("Countries per debt category")
        cc = cs["debt_category"].value_counts().reindex(CAT_ORDER).fillna(0).reset_index()
        cc.columns = ["debt_category", "countries"]
        fig = px.bar(cc, x="countries", y="debt_category", orientation="h", color="debt_category",
                     color_discrete_map=CAT_COLOR, template=TEMPLATE, text="countries",
                     labels={"countries": "Countries", "debt_category": ""})
        fig.update_layout(showlegend=False, height=260, margin=dict(l=0, r=10, t=10, b=0))
        fig.update_yaxes(categoryorder="array", categoryarray=CAT_ORDER[::-1])
        st.plotly_chart(fig, width="stretch")
        st.subheader("Share by indicator group")
        g = eda.group_summary(sub).head(6)
        st.plotly_chart(hbar(g, "pct_of_global", "indicator_group", "% of total debt",
                             fmt="%{x:.1f}%", height=280), width="stretch")

    st.subheader("Total debt by region and country")
    fig = px.treemap(cs, path=[px.Constant("All"), "region", "country_name"], values="total_debt_billion",
                     color="total_debt_billion", color_continuous_scale=SEQ_BLUE)
    fig.update_traces(hovertemplate="%{label}<br>$%{value:,.1f}B<extra></extra>")
    fig.update_layout(height=480, margin=dict(l=0, r=0, t=10, b=0), coloraxis_showscale=False)
    st.plotly_chart(fig, width="stretch")


# ══════════════════════════════════════════════════════════════
# 2. COUNTRY ANALYSIS
# ══════════════════════════════════════════════════════════════
elif page == "Country Analysis":
    st.title("Country Analysis")
    names = cs_all.sort_values("country_name")["country_name"].tolist()
    selected = st.selectbox("Select a country", names, index=names.index("India") if "India" in names else 0)
    row = cs_all[cs_all["country_name"] == selected].iloc[0]
    cdf = df[df["country_name"] == selected]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total debt (all indicators)", f"${row.total_debt_billion:,.1f}B")
    c2.metric("External debt stock", f"${row.external_debt_stock_billion:,.1f}B")
    c3.metric("Global rank", f"#{int(row.debt_rank)} of {len(cs_all)}")
    c4.metric("Category", row.debt_category)
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("% of global total", f"{row.pct_of_global:.2f}%")
    c6.metric("Debt / GNI", "n/a" if pd.isna(row.debt_to_gni_pct) else f"{row.debt_to_gni_pct:.1f}%")
    c7.metric("Debt / exports", "n/a" if pd.isna(row.debt_to_exports_pct) else f"{row.debt_to_exports_pct:.0f}%")
    c8.metric("Reserves / debt", "n/a" if pd.isna(row.reserves_to_debt_pct) else f"{row.reserves_to_debt_pct:.0f}%")
    st.caption(f"Region: **{row.region}** · Income group: **{row.income_group}** · "
               f"{len(cdf)} indicators reported")

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Top 15 debt indicators")
        top = cdf.nlargest(15, "debt_usd").assign(label=lambda d: d["indicator_name"].map(short))
        st.plotly_chart(hbar(top, "debt_billion_usd", "label", "Billion USD", fmt="$%{x:,.2f}B"),
                        width="stretch")
    with right:
        st.subheader("By indicator group")
        g = eda.group_summary(cdf)
        st.plotly_chart(hbar(g, "pct_of_global", "indicator_group", "% of country total", fmt="%{x:.1f}%"),
                        width="stretch")

    with st.expander(f"All {len(cdf)} indicator values for {selected}"):
        st.dataframe(cdf.sort_values("debt_usd", ascending=False)[
            ["indicator_group", "indicator_name", "indicator_code", "debt_billion_usd"]],
            hide_index=True, width="stretch")

    st.divider()
    st.subheader("Compare countries")
    compare = st.multiselect("Countries", names, default=[selected] + [n for n in ["China", "Brazil"] if n != selected])
    measure = st.radio("Measure", ["External debt stock", "Total debt (all indicators)", "Debt / GNI %"],
                       horizontal=True)
    col = {"External debt stock": "external_debt_stock_billion",
           "Total debt (all indicators)": "total_debt_billion", "Debt / GNI %": "debt_to_gni_pct"}[measure]
    if compare:
        comp = cs_all[cs_all["country_name"].isin(compare)].sort_values(col, ascending=False)
        st.plotly_chart(hbar(comp, col, "country_name", measure,
                             fmt="%{x:.1f}%" if "GNI" in measure else "$%{x:,.1f}B"), width="stretch")


# ══════════════════════════════════════════════════════════════
# 3. INDICATOR ANALYSIS
# ══════════════════════════════════════════════════════════════
elif page == "Indicator Analysis":
    st.title("Indicator Analysis")
    groups = ["All groups"] + grp_all["indicator_group"].tolist()
    gsel = st.selectbox("Indicator group", groups)
    ind = ind_all if gsel == "All groups" else ind_all[ind_all["indicator_group"] == gsel]

    c1, c2, c3 = st.columns(3)
    c1.metric("Indicators", len(ind))
    c2.metric("Total value", f"${ind['total_debt_usd'].sum() / 1e12:,.2f}T")
    c3.metric("Share of all debt", f"{ind['pct_of_global'].sum():.1f}%")

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Top 15 indicators by total value")
        top = ind.head(15).assign(label=lambda d: d["indicator_name"].map(short))
        st.plotly_chart(hbar(top, "total_debt_billion", "label", "Billion USD"), width="stretch")
    with right:
        st.subheader("Indicator groups")
        st.plotly_chart(hbar(grp_all, "pct_of_global", "indicator_group", "% of total debt", fmt="%{x:.1f}%"),
                        width="stretch")

    st.divider()
    st.subheader("Top countries for one indicator")
    pick = st.selectbox("Indicator", ind["indicator_name"].tolist())
    n = st.slider("How many countries", 3, 25, 10)
    idf = df[df["indicator_name"] == pick].nlargest(n, "debt_usd")
    st.plotly_chart(hbar(idf, "debt_billion_usd", "country_name", "Billion USD", fmt="$%{x:,.2f}B"),
                    width="stretch")

    st.subheader("Heatmap: top 10 countries x top 8 indicators")
    tc = cs_all.head(10)["country_name"]
    ti = ind_all.head(8)["indicator_name"]
    piv = (df[df["country_name"].isin(tc) & df["indicator_name"].isin(ti)]
           .pivot_table(index="country_name", columns="indicator_name", values="debt_billion_usd", aggfunc="sum")
           .reindex(index=tc, columns=ti))
    fig = go.Figure(go.Heatmap(z=piv.values, x=[short(c, 30) for c in piv.columns], y=piv.index,
                               colorscale=[[0, SEQ_BLUE[0]], [1, SEQ_BLUE[-1]]], xgap=2, ygap=2,
                               colorbar=dict(title="B USD"),
                               hovertemplate="%{y}<br>%{x}<br>$%{z:,.1f}B<extra></extra>"))
    fig.update_layout(template=TEMPLATE, height=480, margin=dict(l=0, r=0, t=10, b=0), xaxis_tickangle=-30)
    st.plotly_chart(fig, width="stretch")


# ══════════════════════════════════════════════════════════════
# 4. DEBT CATEGORIES & CONCENTRATION
# ══════════════════════════════════════════════════════════════
elif page == "Debt Categories":
    st.title("Debt Categories & Concentration")
    st.caption(f"High ≥ ${config.HIGH_DEBT_THRESHOLD / 1e9:,.0f}B · Medium ≥ ${config.LOW_DEBT_THRESHOLD / 1e9:,.0f}B "
               "· Low below that (75th / 25th percentile of country totals).")
    cs = filtered_cs()
    if cs.empty:
        st.warning("No countries match the selected filters.")
        st.stop()
    cols = st.columns(3)
    for col, cat in zip(cols, CAT_ORDER):
        part = cs[cs["debt_category"] == cat]
        col.metric(cat, f"{len(part)} countries", f"{part['pct_of_global'].sum():.1f}% of global debt",
                   delta_color="off")

    pick = st.selectbox("Show countries in", CAT_ORDER)
    st.dataframe(cs[cs["debt_category"] == pick][
        ["debt_rank", "country_name", "region", "income_group", "total_debt_billion", "pct_of_global"]]
        .rename(columns={"debt_rank": "Rank", "country_name": "Country", "region": "Region",
                         "income_group": "Income group", "total_debt_billion": "Total debt (B USD)",
                         "pct_of_global": "% of global"}).round(2), hide_index=True, width="stretch")

    st.divider()
    st.subheader("How concentrated is global debt?")
    cum = cs_all[["debt_rank", "country_name", "cumulative_pct"]]
    n80 = int((cum["cumulative_pct"] < 80).sum()) + 1
    fig = px.line(cum, x="debt_rank", y="cumulative_pct", template=TEMPLATE, hover_name="country_name",
                  labels={"debt_rank": "Countries ranked by total debt", "cumulative_pct": "Cumulative % of total"})
    fig.update_traces(line_color=BLUE, line_width=2)
    fig.add_hline(y=80, line_dash="dash", line_color="#59636e", annotation_text=f"80% reached at {n80} countries")
    fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), yaxis_range=[0, 102])
    st.plotly_chart(fig, width="stretch")

    st.subheader("Countries holding more than 5% of global debt")
    big = cs_all[cs_all["pct_of_global"] > 5]
    st.plotly_chart(hbar(big, "pct_of_global", "country_name", "% of global total", fmt="%{x:.2f}%"),
                    width="stretch")


# ══════════════════════════════════════════════════════════════
# 5. DEBT BURDEN
# ══════════════════════════════════════════════════════════════
elif page == "Debt Burden (vs GNI)":
    st.title("Debt Burden: debt relative to the size of the economy")
    st.caption("External debt stock ÷ GNI. A country with a small total can still be the most stretched.")
    cs = filtered_cs().dropna(subset=["debt_to_gni_pct"])
    if cs.empty:
        st.warning("No countries match the selected filters.")
        st.stop()
    c1, c2, c3 = st.columns(3)
    c1.metric("Median debt / GNI", f"{cs['debt_to_gni_pct'].median():.1f}%")
    c2.metric("Countries above 60%", int((cs["debt_to_gni_pct"] > 60).sum()))
    c3.metric("Countries above 100%", int((cs["debt_to_gni_pct"] > 100).sum()))

    left, right = st.columns(2)
    with left:
        st.subheader("Highest debt / GNI")
        st.plotly_chart(hbar(cs.nlargest(15, "debt_to_gni_pct"), "debt_to_gni_pct", "country_name",
                             "Debt / GNI (%)", color="#d03b3b", fmt="%{x:.0f}%"), width="stretch")
    with right:
        st.subheader("By income group")
        inc = eda.segment_summary(cs, "income_group")
        st.plotly_chart(hbar(inc, "debt_to_gni_pct", "income_group", "Debt / GNI (%)", fmt="%{x:.1f}%"),
                        width="stretch")
        st.subheader("By region")
        reg = eda.segment_summary(cs, "region")
        st.plotly_chart(hbar(reg, "debt_to_gni_pct", "region", "Debt / GNI (%)", fmt="%{x:.1f}%"),
                        width="stretch")

    st.subheader("External debt stock vs GNI")
    fig = px.scatter(cs, x="gni_usd", y="external_debt_stock_usd", color="region", hover_name="country_name",
                     log_x=True, log_y=True, template=TEMPLATE, color_discrete_sequence=CATEGORICAL,
                     labels={"gni_usd": "GNI (USD, log)", "external_debt_stock_usd": "External debt stock (USD, log)"})
    lo, hi = cs["gni_usd"].min(), cs["gni_usd"].max()
    fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", name="debt = GNI",
                             line=dict(color="#59636e", dash="dash", width=1)))
    fig.update_traces(marker=dict(size=9, line=dict(width=1, color="white")), selector=dict(mode="markers"))
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width="stretch")


# ══════════════════════════════════════════════════════════════
# 6. SQL QUERY RESULTS
# ══════════════════════════════════════════════════════════════
elif page == "SQL Query Results":
    st.title("30 SQL Analytical Queries")
    st.caption(f"Each query runs live against the database ({DB_LABEL}). Source: `sql/01-03_*.sql`.")
    bank = load_query_bank()
    tabs = st.tabs(["Basic (Q1-Q10)", "Intermediate (Q11-Q20)", "Advanced (Q21-Q30)"])
    for tab, cat in zip(tabs, ["Basic", "Intermediate", "Advanced"]):
        with tab:
            qs = [q for q in bank if q["category"] == cat]
            labels = [f"{q['id']}: {q['title']}" for q in qs]
            pick = st.selectbox("Question", labels, key=f"q_{cat}")
            q = qs[labels.index(pick)]
            st.markdown(f"**Why:** {q['why']}")
            st.code(q["sql"], language="sql")
            res = run_query(q["sql"])
            st.dataframe(res, hide_index=True, width="stretch")
            st.caption(f"{len(res):,} row(s)")
            st.download_button("Download CSV", res.to_csv(index=False).encode(), f"{q['id']}.csv", "text/csv",
                               key=f"dl_{cat}")


# ══════════════════════════════════════════════════════════════
# 7. INSIGHTS
# ══════════════════════════════════════════════════════════════
elif page == "Insights":
    st.title("Insights & Recommendations")
    st.caption("Every number below is computed live from the database.")
    cs = cs_all
    ratio = cs.dropna(subset=["debt_to_gni_pct"]).sort_values("debt_to_gni_pct", ascending=False)
    inc = eda.segment_summary(cs, "income_group").set_index("income_group")
    reg = eda.segment_summary(cs, "region")
    n80 = int((cs["cumulative_pct"] < 80).sum()) + 1
    top5 = cs.head(5)
    low10 = cs.tail(10)
    stocks = grp_all[grp_all["indicator_group"] == "Debt Stocks"].iloc[0]
    service = grp_all[grp_all["indicator_group"] == "Debt Service"].iloc[0]
    interest = grp_all[grp_all["indicator_group"] == "Interest Payments"].iloc[0]
    cats = cs["debt_category"].value_counts()

    def card(title, body):
        with st.container(border=True):
            st.markdown(f"#### {title}")
            st.markdown(body)

    st.subheader("Key findings")
    a, b = st.columns(2)
    with a:
        card("1. Debt is concentrated in a few countries",
             f"**{cs.iloc[0]['country_name']}** alone holds **{cs.iloc[0]['pct_of_global']:.1f}%** of the total. "
             f"The top 5 ({', '.join(top5['country_name'])}) hold **{top5['pct_of_global'].sum():.1f}%**, and "
             f"just **{n80} of {len(cs)} countries** make up 80% of all debt.")
        card("2. Highest and lowest debt",
             f"Highest: **{cs.iloc[0]['country_name']}** (${cs.iloc[0]['external_debt_stock_billion']:,.0f}B "
             f"external debt stock). Lowest: **{cs.iloc[-1]['country_name']}** "
             f"(${cs.iloc[-1]['total_debt_billion']:,.2f}B total). The bottom 10 countries together hold "
             f"only **{low10['pct_of_global'].sum():.2f}%**.")
        card("3. Debt stocks dominate the indicators",
             f"Debt-stock indicators make up **{stocks['pct_of_global']:.1f}%** of the summed value; debt "
             f"service is **{service['pct_of_global']:.1f}%** and interest **{interest['pct_of_global']:.1f}%**. "
             f"The single largest indicator is *{ind_all.iloc[0]['indicator_name']}*.")
    with b:
        card("4. Size is not the same as burden",
             f"Measured against GNI, the most stretched countries are "
             + ", ".join(f"**{r.country_name}** ({r.debt_to_gni_pct:.0f}%)" for r in ratio.head(4).itertuples())
             + f". China's ratio is only **{cs.iloc[0]['debt_to_gni_pct']:.0f}%**. "
             f"**{int((ratio['debt_to_gni_pct'] > 60).sum())}** countries are above 60% of GNI.")
        card("5. Poorer countries carry the heaviest relative load",
             f"Low-income countries owe **{inc.loc['Low income', 'debt_to_gni_pct']:.0f}%** of their combined GNI, "
             f"compared with **{inc.loc['Upper middle income', 'debt_to_gni_pct']:.0f}%** for upper-middle income. "
             f"By region, **{reg.iloc[0]['region']}** holds the largest stock "
             f"(${reg.iloc[0]['external_debt_stock_billion']:,.0f}B).")
        card("6. Category split",
             f"**{cats.get('High Debt', 0)}** high-debt, **{cats.get('Medium Debt', 0)}** medium-debt and "
             f"**{cats.get('Low Debt', 0)}** low-debt countries. The high-debt group holds "
             f"**{cs[cs.debt_category == 'High Debt']['pct_of_global'].sum():.1f}%** of the total.")

    st.subheader("Recommendations (data-driven decision making)")
    st.markdown(f"""
1. **Judge risk by ratios, not totals.** Rank countries by debt/GNI and debt/exports; the
   top of that list ({', '.join(ratio.head(3)['country_name'])}) needs closer monitoring than the
   largest absolute borrowers.
2. **Watch the concentration.** With {n80} countries holding 80% of the total, a shock in any
   of the top 5 moves the global picture. Track them as a separate watch-list.
3. **Prioritise relief and concessional lending for low-income countries**, whose debt equals
   {inc.loc['Low income', 'debt_to_gni_pct']:.0f}% of their GNI.
4. **Report the external debt stock as the headline figure.** Summing all indicators double-counts
   (sub-totals are included with totals), so use it only for spec-level comparisons.
5. **Follow debt service and interest** (the cash that leaves the country each year) alongside
   stocks, to spot liquidity pressure early.
""")

    st.subheader("Supporting charts")
    l, r = st.columns(2)
    with l:
        st.plotly_chart(hbar(cs.head(10), "pct_of_global", "country_name", "% of global total", fmt="%{x:.1f}%"),
                        width="stretch")
    with r:
        st.plotly_chart(hbar(ratio.head(10), "debt_to_gni_pct", "country_name", "Debt / GNI (%)",
                             color="#d03b3b", fmt="%{x:.0f}%"), width="stretch")


# ══════════════════════════════════════════════════════════════
# 8. POWER BI
# ══════════════════════════════════════════════════════════════
elif page == "Power BI Dashboard":
    st.title("Power BI Dashboard")
    st.markdown("The same data is modelled in Power BI: **`International_Debt_Dashboard.pbix`**, "
                "built on the tables in `powerbi_data/` (also loadable from MySQL). "
                "Setup steps are in `POWERBI_GUIDE.md`.")
    shots = sorted((ROOT / "reports" / "powerbi").glob("*.png"))
    if shots:
        for s in shots:
            st.image(str(s), caption=s.stem.replace("_", " "), width="stretch")
    else:
        st.info("Dashboard screenshots will appear here once they are added to reports/powerbi/.")
    st.markdown("""
| Page | What it shows |
|---|---|
| Overview | KPI cards, Top 10 countries, debt-category donut, country treemap, country slicer + table |
| Indicator Analysis | debt by indicator, category donut, country slicer, country x indicator table |
| Insights | key findings, recommendations, Top 10 by % of global debt |
""")
    c1, c2 = st.columns(2)
    pbix = ROOT / "International_Debt_Dashboard.pbix"
    if pbix.exists():
        c1.download_button("Download the .pbix file", pbix.read_bytes(), pbix.name, "application/octet-stream")
    pdf = ROOT / "reports" / "powerbi" / "International_Debt_Dashboard.pdf"
    if pdf.exists():
        c2.download_button("Download dashboard as PDF", pdf.read_bytes(), pdf.name, "application/pdf")


# ══════════════════════════════════════════════════════════════
# 9. DATA & METHODOLOGY
# ══════════════════════════════════════════════════════════════
elif page == "Data & Methodology":
    st.title("Data & Methodology")
    st.markdown("""
**Pipeline:** raw CSV → pandas DataFrame → cleaning → normalised tables → MySQL / SQLite
(primary & foreign keys) → 30 SQL queries → EDA & charts → Streamlit + Power BI.

**Cleaning steps** (`src/preprocessing.py`)
- trimmed whitespace, upper-cased codes, converted `debt_usd` to numeric
- rows with a missing key or value are dropped (a debt figure is never invented)
- exact and (country, indicator) duplicates removed
- negative values rejected
- **5 macro-economic indicators** (GNI, exports, imports, reserves, current account) moved out of the
  debt table into `country_macro`. They are not debt, and keeping them inflated "total debt" by
  $61.7T (China's GNI alone is $18.2T).
- added region / income group from the World Bank country metadata and an `indicator_group` per indicator
""")
    st.subheader("Database schema")
    st.code("""countries (country_id PK, country_code UNIQUE, country_name, region, income_group, lending_category)
indicators (indicator_id PK, indicator_code UNIQUE, indicator_name, indicator_group)
debt_data (debt_id PK, country_id FK -> countries, indicator_id FK -> indicators,
           debt_usd, debt_billion_usd, UNIQUE(country_id, indicator_id))
country_macro (country_id PK/FK -> countries, gni_usd, exports_usd, imports_usd, reserves_usd, current_account_usd)
views: vw_top10_countries, vw_country_debt_profile""", language="text")
    counts = {t: int(run_query(f"SELECT COUNT(*) AS n FROM {t}")["n"].iloc[0])
              for t in ["countries", "indicators", "debt_data", "country_macro"]}
    st.dataframe(pd.DataFrame(counts.items(), columns=["Table", "Rows"]), hide_index=True)
    st.subheader("Browse the cleaned data")
    st.dataframe(df[["country_name", "region", "indicator_group", "indicator_name", "debt_usd"]].head(500),
                 hide_index=True, width="stretch")
    st.download_button("Download full cleaned dataset (CSV)",
                       df.drop(columns=["debt_id"]).to_csv(index=False).encode(), "international_debt_cleaned.csv",
                       "text/csv")
