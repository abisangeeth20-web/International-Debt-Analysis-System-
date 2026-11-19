"""Add report pages to International_Debt_Dashboard.pbix.

The pbix is a zip; its report layout lives in `Report/Layout` (UTF-16 JSON).
This script rewrites the layout so the report has three pages:
  1. Overview              (the original page, with the Top-10 bar fixed to rank <= 10)
  2. Indicator Analysis    (indicator bar, category donut, country slicer + matrix table)
  3. Insights              (key findings + recommendations text, % share chart)
Only tables already in the data model are used, so no model change is needed.
After running it, open the pbix in Power BI Desktop, press Refresh, then Save.

Usage: python powerbi/build_pbix_pages.py
"""
from __future__ import annotations

import json
import shutil
import sys
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PBIX = ROOT / "International_Debt_Dashboard.pbix"
SUMMARY = ROOT / "reports" / "pipeline_summary.json"


def uid() -> str:
    return uuid.uuid4().hex[:20]


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def col(src, prop):
    return {"Column": {"Expression": {"SourceRef": {"Source": src}}, "Property": prop}}


def col_sel(src, entity, prop):
    return {**col(src, prop), "Name": f"{entity}.{prop}", "NativeReferenceName": prop}


def sum_sel(src, entity, prop, label=None):
    return {"Aggregation": {"Expression": col(src, prop), "Function": 0},
            "Name": f"Sum({entity}.{prop})", "NativeReferenceName": label or f"Sum of {prop}"}


def title(text, size="14D"):
    return {"title": [{"properties": {"text": lit(f"'{text}'"), "fontSize": lit(size), "bold": lit("true")}}]}


def container(cfg, x, y, w, h, z, filters="[]"):
    cfg["layouts"] = [{"id": 0, "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": z}}]
    return {"x": x, "y": y, "z": z, "width": w, "height": h, "config": json.dumps(cfg), "filters": filters}


def textbox(paragraphs, x, y, w, h, z):
    """paragraphs: list of list of (text, style dict)."""
    paras = [{"textRuns": [{"value": t, **({"textStyle": s} if s else {})} for t, s in runs]} for runs in paragraphs]
    cfg = {"name": uid(), "singleVisual": {"visualType": "textbox", "drillFilterOtherVisuals": True,
                                           "objects": {"general": [{"properties": {"paragraphs": paras}}]}}}
    return container(cfg, x, y, w, h, z)


def bar_chart(entity, alias, cat, val, ttl, x, y, w, h, z, filters="[]", label=None):
    cfg = {"name": uid(), "singleVisual": {
        "visualType": "clusteredBarChart",
        "projections": {"Category": [{"queryRef": f"{entity}.{cat}", "active": True}],
                        "Y": [{"queryRef": f"Sum({entity}.{val})"}]},
        "prototypeQuery": {"Version": 2, "From": [{"Name": alias, "Entity": entity, "Type": 0}],
                           "Select": [col_sel(alias, entity, cat), sum_sel(alias, entity, val, label)],
                           "OrderBy": [{"Direction": 2, "Expression": {"Aggregation": {
                               "Expression": col(alias, val), "Function": 0}}}]},
        "drillFilterOtherVisuals": True, "hasDefaultSort": True,
        "objects": {"labels": [{"properties": {"show": lit("true")}}],
                    "valueAxis": [{"properties": {"gridlineShow": lit("false")}}]},
        "vcObjects": title(ttl)}}
    return container(cfg, x, y, w, h, z, filters)


def donut(entity, alias, cat, val, ttl, x, y, w, h, z):
    cfg = {"name": uid(), "singleVisual": {
        "visualType": "donutChart",
        "projections": {"Category": [{"queryRef": f"{entity}.{cat}", "active": True}],
                        "Y": [{"queryRef": f"Sum({entity}.{val})"}]},
        "prototypeQuery": {"Version": 2, "From": [{"Name": alias, "Entity": entity, "Type": 0}],
                           "Select": [col_sel(alias, entity, cat), sum_sel(alias, entity, val)]},
        "drillFilterOtherVisuals": True,
        "objects": {"labels": [{"properties": {"show": lit("true"), "labelStyle": lit("'Category, data value'")}}]},
        "vcObjects": title(ttl)}}
    return container(cfg, x, y, w, h, z)


def slicer(entity, alias, column, ttl, x, y, w, h, z):
    cfg = {"name": uid(), "singleVisual": {
        "visualType": "slicer",
        "projections": {"Values": [{"queryRef": f"{entity}.{column}", "active": True}]},
        "prototypeQuery": {"Version": 2, "From": [{"Name": alias, "Entity": entity, "Type": 0}],
                           "Select": [col_sel(alias, entity, column)]},
        "drillFilterOtherVisuals": True,
        "objects": {"data": [{"properties": {"mode": lit("'Dropdown'")}}]},
        "vcObjects": title(ttl, "12D")}}
    return container(cfg, x, y, w, h, z)


def table(entity, alias, cols, sum_col, ttl, x, y, w, h, z):
    sels = [col_sel(alias, entity, c) for c in cols] + [sum_sel(alias, entity, sum_col)]
    cfg = {"name": uid(), "singleVisual": {
        "visualType": "tableEx",
        "projections": {"Values": [{"queryRef": s["Name"]} for s in sels]},
        "prototypeQuery": {"Version": 2, "From": [{"Name": alias, "Entity": entity, "Type": 0}], "Select": sels,
                           "OrderBy": [{"Direction": 2, "Expression": {"Aggregation": {
                               "Expression": col(alias, sum_col), "Function": 0}}}]},
        "drillFilterOtherVisuals": True,
        "vcObjects": title(ttl)}}
    return container(cfg, x, y, w, h, z)


def rank_filter(entity, max_rank=10):
    return json.dumps([{
        "name": uid(),
        "expression": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": "debt_rank"}},
        "filter": {"Version": 2, "From": [{"Name": "c", "Entity": entity, "Type": 0}],
                   "Where": [{"Condition": {"Comparison": {"ComparisonKind": 4,
                                                           "Left": col("c", "debt_rank"),
                                                           "Right": {"Literal": {"Value": f"{max_rank}L"}}}}}]},
        "type": "Advanced", "howCreated": 1}])


def section(name, display, ordinal, visuals, template):
    s = {k: v for k, v in template.items() if k not in ("visualContainers", "id", "name", "displayName", "ordinal")}
    s.update({"id": ordinal, "name": name, "displayName": display, "ordinal": ordinal, "visualContainers": visuals,
              "filters": "[]"})
    return s


def insights_text(f: dict) -> list:
    H = {"fontWeight": "bold", "fontSize": "14pt"}
    B = {"fontWeight": "bold"}
    cats = f["category_counts"]
    gni = ", ".join(f"{c} ({v:.0f}%)" for c, v in f["highest_debt_to_gni"][:3])
    return [
        [("Key findings", H)],
        [("1. Concentration: ", B), (f"{f['top_country']} holds {f['top_country_pct']:.1f}% of total debt; the top 5 "
                                     f"({', '.join(f['top5_countries'])}) hold {f['top5_pct']:.1f}%. "
                                     f"Only {f['countries_for_80pct']} of {f['countries']} countries make up 80%.", None)],
        [("2. Highest / lowest: ", B), (f"{f['top_country']} is the most indebted; {f['lowest_country']} the least "
                                        f"(${f['lowest_country_billion']:.2f}B).", None)],
        [("3. Indicators: ", B), (f"{f['top_group']} make up {f['top_group_pct']:.1f}% of the summed value; the largest "
                                  f"single indicator is '{f['top_indicator']}'.", None)],
        [("4. Burden vs size: ", B), (f"Relative to GNI the most stretched are {gni}. "
                                      f"{f['countries_debt_over_gni_60']} countries owe more than 60% of GNI.", None)],
        [("5. Categories: ", B), (f"{cats.get('High Debt', 0)} High, {cats.get('Medium Debt', 0)} Medium and "
                                  f"{cats.get('Low Debt', 0)} Low debt countries.", None)],
        [("", None)],
        [("Recommendations", H)],
        [("- Rank risk by debt/GNI and debt/exports, not by totals alone.", None)],
        [("- Keep the top 5 borrowers on a watch-list: they move the global total.", None)],
        [("- Prioritise relief and concessional finance for low-income, high-ratio countries.", None)],
        [("- Use the external debt stock as the headline figure; summed indicators double-count.", None)],
    ]


def main() -> int:
    if not PBIX.exists():
        print("pbix not found:", PBIX)
        return 1
    findings = json.loads(SUMMARY.read_text(encoding="utf-8"))["findings"]
    with zipfile.ZipFile(PBIX) as z:
        infos = z.infolist()
        entries = {i.filename: z.read(i.filename) for i in infos}
        compress = {i.filename: i.compress_type for i in infos}
    layout = json.loads(entries["Report/Layout"].decode("utf-16-le").lstrip("﻿"))

    overview = layout["sections"][0]
    overview["displayName"] = "Overview"
    for vc in overview["visualContainers"]:
        cfg = json.loads(vc["config"])
        if cfg["singleVisual"]["visualType"] == "clusteredBarChart":
            vc["filters"] = rank_filter("country_debt_summary")
            vc.pop("query", None)
            vc.pop("dataTransforms", None)
    layout["sections"] = [overview]

    p2 = [
        textbox([[("Indicator & Country Analysis", {"fontWeight": "bold", "fontSize": "22pt"})]], 40, 10, 900, 55, 0),
        bar_chart("indicator_debt_summary", "i", "indicator_name", "total_debt_billion",
                  "Total debt by indicator (billion USD)", 40, 70, 600, 630, 1),
        donut("debt_categories", "d", "debt_category", "country_count", "Countries per debt category",
              660, 70, 580, 250, 2),
        slicer("country_indicator_matrix", "m", "country_name", "Select country", 660, 330, 580, 70, 3),
        table("country_indicator_matrix", "m", ["country_name", "indicator_name"], "debt_billion",
              "Country x indicator detail (billion USD)", 660, 410, 580, 290, 4),
    ]
    p3 = [
        textbox([[("Insights & Recommendations", {"fontWeight": "bold", "fontSize": "22pt"})]], 40, 10, 900, 55, 0),
        textbox(insights_text(findings), 40, 70, 640, 630, 1),
        bar_chart("country_debt_summary", "c", "country_name", "pct_of_global",
                  "Top 10 countries: % of global debt", 700, 70, 540, 630, 2,
                  filters=rank_filter("country_debt_summary"), label="% of global debt"),
    ]
    layout["sections"].append(section(uid(), "Indicator Analysis", 1, p2, overview))
    layout["sections"].append(section(uid(), "Insights", 2, p3, overview))
    cfg = json.loads(layout["config"])
    cfg["activeSectionIndex"] = 0
    layout["config"] = json.dumps(cfg)

    entries["Report/Layout"] = json.dumps(layout, ensure_ascii=False).encode("utf-16-le")
    # Power BI rejects an edited layout while the old SecurityBindings blob is present
    entries.pop("SecurityBindings", None)
    ct = entries["[Content_Types].xml"].decode("utf-8-sig")
    ct = ct.replace('<Override PartName="/SecurityBindings" ContentType="" />', "")
    entries["[Content_Types].xml"] = b"\xef\xbb\xbf" + ct.encode("utf-8")

    tmp = PBIX.with_suffix(".tmp.pbix")
    with zipfile.ZipFile(tmp, "w") as z:
        for name, data in entries.items():  # keep original order and per-entry compression
            z.writestr(name, data, compress_type=compress.get(name, zipfile.ZIP_DEFLATED))
    shutil.move(tmp, PBIX)
    print("pbix updated: pages =", [s["displayName"] for s in layout["sections"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
