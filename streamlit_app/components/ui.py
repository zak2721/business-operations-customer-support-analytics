"""Shared UI components: page setup, KPI cards, Plotly chart helpers, downloads."""
from __future__ import annotations

import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.visualization.theme import PLOTLY_LAYOUT, SERIES, STATUS

CSS = """
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1400px;}
h1 {font-size: 1.6rem !important; letter-spacing: -.01em;}
.kpi-row {display: grid; grid-template-columns: repeat(auto-fit, minmax(132px, 1fr)); gap: 10px; margin: .2rem 0 1rem;}
.kpi {background: #fff; border: 1px solid #e1e4e9; border-radius: 10px; padding: 12px 14px;}
.kpi .l {font-size: 12px; color: #4a5361; font-weight: 600;}
.kpi .v {font-size: 24px; font-weight: 700; color: #141920; font-variant-numeric: tabular-nums; line-height: 1.25;}
.kpi .h {font-size: 11px; color: #7b8492;}
.kpi.good {box-shadow: inset 0 3px 0 #0ca30c;} .kpi.warn {box-shadow: inset 0 3px 0 #fab219;} .kpi.crit {box-shadow: inset 0 3px 0 #d03b3b;}
div[data-testid="stPlotlyChart"] {background: #fff; border: 1px solid #e1e4e9; border-radius: 10px; padding: 6px;}
.note {font-size: 12px; color: #7b8492;}
</style>
"""


def page_setup(title: str, subtitle: str) -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.title(title)
    st.caption(subtitle)


def _fmt(v, kind: str) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    return {"int": f"{v:,.0f}", "pct": f"{v:.1f}%", "h": f"{v:.1f} h", "min": f"{v:.2f} min", "csat": f"{v:.2f} / 5",
            "usd": (f"${v/1e6:,.2f}M" if v >= 1e6 else f"${v:,.0f}" if v >= 100 else f"${v:,.3f}"),
            "num": f"{v:,.1f}"}[kind]


def kpi_cards(items: list[tuple]) -> None:
    """items: (label, value, kind[, hint[, status]]) where status in good/warn/crit."""
    html = []
    for it in items:
        label, val, kind = it[:3]
        hint = it[3] if len(it) > 3 else ""
        status = it[4] if len(it) > 4 else ""
        html.append(f'<div class="kpi {status}"><div class="l">{label}</div><div class="v">{_fmt(val, kind)}</div>'
                    f'<div class="h">{hint}</div></div>')
    st.markdown(f'<div class="kpi-row">{"".join(html)}</div>', unsafe_allow_html=True)


def sla_status(pct: float) -> str:
    if pct is None or (isinstance(pct, float) and math.isnan(pct)):
        return ""
    return "good" if pct >= 85 else "warn" if pct >= 70 else "crit"


def style(fig: go.Figure, title: str, height: int = 340, legend: bool | None = None) -> go.Figure:
    fig.update_layout(**PLOTLY_LAYOUT, height=height)
    fig.update_layout(title_text=title)
    if legend is not None:
        fig.update_layout(showlegend=legend)
    return fig


def bar(df: pd.DataFrame, x: str, y: str, title: str, horizontal: bool = True, fmt: str = ",.0f",
        color: str | list | None = None, height: int = 340, sort: bool = True) -> go.Figure:
    d = df.sort_values(x if horizontal else y, ascending=True) if sort and horizontal else df
    if horizontal:
        fig = go.Figure(go.Bar(y=d[y].astype(str), x=d[x], orientation="h", marker_color=color or SERIES[0],
                               texttemplate=f"%{{x:{fmt}}}", textposition="outside", cliponaxis=False,
                               hovertemplate=f"%{{y}}: %{{x:{fmt}}}<extra></extra>"))
    else:
        fig = go.Figure(go.Bar(x=d[x].astype(str), y=d[y], marker_color=color or SERIES[0],
                               texttemplate=f"%{{y:{fmt}}}", textposition="outside", cliponaxis=False,
                               hovertemplate=f"%{{x}}: %{{y:{fmt}}}<extra></extra>"))
    vmax = float(d[x if horizontal else y].max()) if len(d) else 0
    if vmax > 0:
        (fig.update_xaxes if horizontal else fig.update_yaxes)(range=[0, vmax * 1.28])
    return style(fig, title, height, legend=False)


def line(df: pd.DataFrame, x: str, ys: list[str], title: str, names: list[str] | None = None, fmt: str = ",.1f",
         height: int = 340, ref: float | None = None, ref_label: str = "") -> go.Figure:
    fig = go.Figure()
    for i, y in enumerate(ys):
        fig.add_trace(go.Scatter(x=df[x], y=df[y], mode="lines", name=(names or ys)[i], line=dict(width=2, color=SERIES[i]),
                                 hovertemplate=f"%{{x}}: %{{y:{fmt}}}<extra>{(names or ys)[i]}</extra>"))
    if ref is not None:
        fig.add_hline(y=ref, line_dash="dash", line_color="#898781", annotation_text=ref_label, annotation_position="top left")
    return style(fig, title, height, legend=len(ys) > 1)


def status_colors(values, good: float = 85, warn: float = 70) -> list[str]:
    return [STATUS["good"] if v >= good else STATUS["warning"] if v >= warn else STATUS["critical"] for v in values]


def heatmap(m: pd.DataFrame, title: str, height: int = 320) -> go.Figure:
    fig = px.imshow(m, color_continuous_scale=["#f4f8fd", "#9ec5f4", "#3987e5", "#184f95", "#0d366b"], aspect="auto")
    fig.update_traces(hovertemplate="%{y} %{x}:00 · %{z:,} tickets<extra></extra>")
    return style(fig, title, height)


def download(df: pd.DataFrame, label: str, filename: str) -> None:
    st.download_button(f"⬇ {label}", df.to_csv(index=False).encode("utf-8"), file_name=filename, mime="text/csv")


def empty_guard(df: pd.DataFrame) -> None:
    if df.empty:
        st.warning("No records match the current filters. Widen the date range or clear a filter.")
        st.stop()
