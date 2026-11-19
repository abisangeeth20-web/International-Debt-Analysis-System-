"""Static (Matplotlib / Seaborn) and interactive (Plotly) charts for the EDA report."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import plotly.express as px
import seaborn as sns

from . import config

# Validated palette (dataviz skill reference palette)
BLUE = "#2a78d6"
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]
CATEGORICAL = ["#2a78d6", "#008300", "#e87ba4", "#eda100", "#1baf7a", "#eb6834", "#4a3aa7", "#e34948"]
STATUS = {"good": "#0ca30c", "warning": "#fab219", "critical": "#d03b3b"}
CAT_COLOR = {"High Debt": STATUS["critical"], "Medium Debt": STATUS["warning"], "Low Debt": STATUS["good"]}
INK, MUTED, GRID = "#1f2328", "#59636e", "#e6e8eb"

sns.set_theme(style="whitegrid", rc={
    "axes.edgecolor": GRID, "grid.color": GRID, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.titleweight": "bold", "axes.titlesize": 13,
    "font.size": 10,
})


def _short(s: str, n: int = 48) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def short_indicator(name: str) -> str:
    """'External debt stocks, long-term (DOD, current US$)' -> 'Stocks: long-term'."""
    import re
    s = re.sub(r"\s*\((DOD|TDS|AMT|INT|DIS|NFL|NTR|COM|UND)?,?\s*current US\$\)", "", name)
    s = s.replace("External debt stocks, ", "Stocks: ").replace("Debt service on external debt, ", "Service: ")
    s = s.replace("public and publicly guaranteed (PPG)", "PPG").replace("private nonguaranteed (PNG)", "PNG")
    return _short(s, 34)


def _billions(ax, axis="x"):
    fmt = mticker.FuncFormatter(lambda x, _: f"${x:,.0f}B")
    (ax.xaxis if axis == "x" else ax.yaxis).set_major_formatter(fmt)


def _save(fig, name: str) -> str:
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = config.FIGURES_DIR / name
    fig.tight_layout()
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return name


def _hbar(df, value, label, title, xlabel, name, color=BLUE, fmt="${:,.0f}B"):
    fig, ax = plt.subplots(figsize=(10, 0.42 * len(df) + 1.4))
    d = df.iloc[::-1]
    ax.barh([_short(x) for x in d[label]], d[value], color=color, height=0.65)
    for y, v in enumerate(d[value]):
        ax.text(v, y, " " + fmt.format(v), va="center", fontsize=8.5, color=MUTED)
    ax.set_title(title, loc="left")
    ax.set_xlabel(xlabel)
    ax.margins(x=0.15)
    ax.grid(axis="y", visible=False)
    return _save(fig, name)


def make_all(df: pd.DataFrame, cs: pd.DataFrame, ind: pd.DataFrame, grp: pd.DataFrame,
             region: pd.DataFrame, corr: pd.DataFrame) -> list[str]:
    saved = []

    saved.append(_hbar(cs.head(10), "total_debt_billion", "country_name",
                       "Top 10 countries by total debt (all debt indicators)", "Total debt (billion USD)",
                       "eda_01_top10_countries.png"))
    saved.append(_hbar(cs.tail(10).iloc[::-1], "total_debt_billion", "country_name",
                       "10 countries with the lowest total debt", "Total debt (billion USD)",
                       "eda_02_bottom10_countries.png", color=SEQ_BLUE[3], fmt="${:,.2f}B"))

    # Category distribution
    order = ["High Debt", "Medium Debt", "Low Debt"]
    counts = cs["debt_category"].value_counts().reindex(order).fillna(0)
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.barh(order[::-1], counts[order[::-1]], color=[CAT_COLOR[c] for c in order[::-1]], height=0.6)
    for y, v in enumerate(counts[order[::-1]]):
        ax.text(v, y, f" {int(v)} countries", va="center", color=MUTED)
    ax.set_title("Countries per debt category (75th / 25th percentile thresholds)", loc="left")
    ax.set_xlabel("Number of countries")
    ax.margins(x=0.2)
    ax.grid(axis="y", visible=False)
    saved.append(_save(fig, "eda_03_debt_categories.png"))

    saved.append(_hbar(grp, "pct_of_global", "indicator_group", "Share of total debt by indicator group",
                       "% of total debt", "eda_04_indicator_groups.png", fmt="{:.1f}%"))
    saved.append(_hbar(ind.head(15).assign(indicator_name=ind.head(15)["indicator_name"].map(short_indicator)),
                       "total_debt_billion", "indicator_name",
                       "Top 15 indicators by total value", "Total (billion USD)", "eda_05_top_indicators.png"))

    # Heatmap: top 10 countries x top 8 indicators
    top_c = cs.head(10)["country_name"]
    top_i = ind.head(8)["indicator_name"]
    piv = (df[df["country_name"].isin(top_c) & df["indicator_name"].isin(top_i)]
           .pivot_table(index="country_name", columns="indicator_name", values="debt_billion_usd", aggfunc="sum")
           .reindex(index=top_c, columns=top_i))
    piv.columns = [short_indicator(c) for c in piv.columns]
    fig, ax = plt.subplots(figsize=(13, 6.5))
    sns.heatmap(piv, annot=True, fmt=",.0f", cmap=sns.color_palette(SEQ_BLUE, as_cmap=True), linewidths=2,
                linecolor="white", cbar_kws={"label": "Billion USD"}, ax=ax)
    ax.set_title("Top 10 countries x top 8 indicators (billion USD)", loc="left")
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.xticks(rotation=35, ha="right")
    saved.append(_save(fig, "eda_06_country_indicator_heatmap.png"))

    # Distribution of single values (log scale)
    fig, ax = plt.subplots(figsize=(10, 4))
    sns.histplot(np.log10(df["debt_usd"].clip(lower=1)), bins=50, color=BLUE, ax=ax)
    ax.set_title("Distribution of individual debt values (log scale)", loc="left")
    ax.set_xlabel("Debt value (USD, log10): 6 = $1M, 9 = $1B, 12 = $1T")
    ax.set_ylabel("Records")
    saved.append(_save(fig, "eda_07_value_distribution.png"))

    # Pareto: cumulative % only (one axis)
    fig, ax = plt.subplots(figsize=(10, 4))
    x = np.arange(1, len(cs) + 1)
    ax.plot(x, cs["cumulative_pct"], color=BLUE, linewidth=2)
    ax.axhline(80, color=MUTED, linestyle="--", linewidth=1)
    n80 = int((cs["cumulative_pct"] < 80).sum()) + 1
    ax.annotate(f"{n80} countries reach 80%", xy=(n80, 80), xytext=(n80 + 8, 62), color=INK,
                arrowprops=dict(arrowstyle="-", color=MUTED))
    ax.set_title("Cumulative share of total debt, countries ranked largest first", loc="left")
    ax.set_xlabel("Number of countries")
    ax.set_ylabel("Cumulative % of total debt")
    ax.set_ylim(0, 102)
    saved.append(_save(fig, "eda_08_pareto_cumulative.png"))

    ratio = cs.dropna(subset=["debt_to_gni_pct"]).sort_values("debt_to_gni_pct", ascending=False).head(15)
    saved.append(_hbar(ratio, "debt_to_gni_pct", "country_name",
                       "Highest external debt stock as % of GNI", "External debt stock / GNI (%)",
                       "eda_09_debt_to_gni.png", color=STATUS["critical"], fmt="{:.0f}%"))
    saved.append(_hbar(region, "external_debt_stock_billion", "region",
                       "External debt stock by region", "External debt stock (billion USD)",
                       "eda_10_region_debt.png"))

    # Correlation heatmap (diverging)
    fig, ax = plt.subplots(figsize=(7, 5.5))
    sns.heatmap(corr, annot=True, fmt=".2f", vmin=-1, vmax=1, cmap="RdBu_r", linewidths=2,
                linecolor="white", ax=ax)
    ax.set_title("Spearman correlation between country measures", loc="left")
    saved.append(_save(fig, "eda_11_correlation.png"))

    # Scatter: external debt stock vs GNI
    sc = cs.dropna(subset=["gni_usd", "external_debt_stock_usd"])
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(sc["gni_usd"] / 1e9, sc["external_debt_stock_billion"], s=36, color=BLUE, alpha=0.75,
               edgecolor="white", linewidth=1)
    lim = [1, max(sc["gni_usd"].max() / 1e9, sc["external_debt_stock_billion"].max()) * 1.5]
    ax.plot(lim, lim, color=MUTED, linestyle="--", linewidth=1)
    ax.text(lim[1] / 3, lim[1] / 2, "debt = GNI", color=MUTED, rotation=35)
    label = pd.concat([sc.nlargest(2, "external_debt_stock_billion"), sc.nlargest(3, "debt_to_gni_pct"),
                       sc[sc["country_name"] == "Turkiye"]]).drop_duplicates("country_id")
    for _, r in label.iterrows():
        ax.annotate(r["country_name"], (r["gni_usd"] / 1e9, r["external_debt_stock_billion"]),
                    xytext=(4, 4), textcoords="offset points", fontsize=8.5, color=INK)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("GNI (billion USD, log)")
    ax.set_ylabel("External debt stock (billion USD, log)")
    ax.set_title("External debt grows with economy size; points above the line owe more than their GNI",
                 loc="left")
    saved.append(_save(fig, "eda_12_debt_vs_gni.png"))

    # Interactive Plotly versions
    inter = config.FIGURES_DIR / "interactive"
    inter.mkdir(parents=True, exist_ok=True)
    f1 = px.treemap(cs, path=[px.Constant("All countries"), "region", "country_name"], values="total_debt_billion",
                    color="total_debt_billion", color_continuous_scale=SEQ_BLUE,
                    title="Total debt by region and country (billion USD)")
    f1.write_html(inter / "treemap_region_country.html", include_plotlyjs="cdn")
    f2 = px.scatter(sc, x="gni_usd", y="external_debt_stock_usd", hover_name="country_name", color="region",
                    log_x=True, log_y=True, color_discrete_sequence=CATEGORICAL,
                    labels={"gni_usd": "GNI (USD)", "external_debt_stock_usd": "External debt stock (USD)"},
                    title="External debt stock vs GNI")
    f2.write_html(inter / "debt_vs_gni.html", include_plotlyjs="cdn")
    f3 = px.bar(cs.head(20).iloc[::-1], x="total_debt_billion", y="country_name", orientation="h",
                color_discrete_sequence=[BLUE], title="Top 20 countries by total debt (billion USD)",
                labels={"total_debt_billion": "Billion USD", "country_name": ""})
    f3.write_html(inter / "top20_countries.html", include_plotlyjs="cdn")
    saved += ["interactive/treemap_region_country.html", "interactive/debt_vs_gni.html",
              "interactive/top20_countries.html"]
    return saved
