"""Reusable matplotlib chart builders (static PNGs for reports, README and notebooks).

Each function takes a tidy DataFrame + column names and returns the Figure.
``save`` writes it to ``visualizations/``.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src import config  # noqa: E402
from src.visualization.theme import INK, PRIMARY, SEQUENTIAL, SERIES, STATUS, apply_matplotlib_theme  # noqa: E402

apply_matplotlib_theme()


def save(fig: plt.Figure, name: str, out_dir: Path = config.VIS_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _subtitle(ax, text: str | None) -> None:
    if text:
        ax.text(0, 1.015, text, transform=ax.transAxes, fontsize=9, color=INK["secondary"], va="bottom")


def _fmt(v: float, fmt: str) -> str:
    """format() with an optional leading '$' prefix (e.g. '$,.0f')."""
    if fmt.startswith("$"):
        return "$" + format(v, fmt[1:])
    return format(v, fmt)


def hbar(df: pd.DataFrame, cat: str, val: str, title: str, xlabel: str, subtitle: str | None = None,
         fmt: str = ",.0f", color: str | list = PRIMARY, sort: bool = True, ref: float | None = None,
         ref_label: str | None = None, figsize=(9, None)) -> plt.Figure:
    d = df.sort_values(val) if sort else df.iloc[::-1]
    h = figsize[1] or max(3.0, 0.42 * len(d) + 1.2)
    fig, ax = plt.subplots(figsize=(figsize[0], h))
    bars = ax.barh(d[cat].astype(str), d[val], color=color, height=0.62)
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    ax.set_xlabel(xlabel); ax.set_title(title)
    _subtitle(ax, subtitle)
    vmax = d[val].max()
    for b, v in zip(bars, d[val]):
        ax.text(b.get_width() + vmax * 0.01, b.get_y() + b.get_height() / 2, _fmt(v, fmt),
                va="center", fontsize=8.5, color=INK["secondary"])
    ax.set_xlim(0, vmax * 1.12)
    if ref is not None:
        ax.axvline(ref, color=INK["muted"], lw=1, ls="--")
        ax.text(ref, len(d) - 0.4, f" {ref_label or ''}", color=INK["secondary"], fontsize=8, va="bottom")
    return fig


def vbar(df: pd.DataFrame, cat: str, val: str, title: str, ylabel: str, subtitle: str | None = None,
         fmt: str = ",.0f", color: str | list = PRIMARY, label_every: int = 1, rotate: int = 0,
         figsize=(9, 4.2)) -> plt.Figure:
    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.bar(df[cat].astype(str), df[val], color=color, width=0.66)
    ax.set_ylabel(ylabel); ax.set_title(title); _subtitle(ax, subtitle)
    vmax = df[val].max()
    for i, (b, v) in enumerate(zip(bars, df[val])):
        if i % label_every == 0:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + vmax * 0.01, _fmt(v, fmt),
                    ha="center", va="bottom", fontsize=8.5, color=INK["secondary"])
    ax.set_ylim(0, vmax * 1.14)
    plt.setp(ax.get_xticklabels(), rotation=rotate, ha="right" if rotate else "center")
    return fig


def line(df: pd.DataFrame, x: str, ys: list[str] | str, title: str, ylabel: str, subtitle: str | None = None,
         labels: list[str] | None = None, pct: bool = False, ylim=None, every: int = 3,
         annotate_last: bool = True, figsize=(10, 4.2), fmt: str = ",.1f") -> plt.Figure:
    ys = [ys] if isinstance(ys, str) else ys
    labels = labels or ys
    fig, ax = plt.subplots(figsize=figsize)
    xs = np.arange(len(df))
    for i, (y, lab) in enumerate(zip(ys, labels)):
        ax.plot(xs, df[y], color=SERIES[i], label=lab, lw=2)
        if annotate_last:
            ax.annotate(_fmt(df[y].iloc[-1], fmt) + ("%" if pct else ""), (xs[-1], df[y].iloc[-1]),
                        xytext=(6, 0), textcoords="offset points", va="center", fontsize=8.5, color=INK["secondary"])
    ax.set_xticks(xs[::every]); ax.set_xticklabels(df[x].astype(str).iloc[::every], rotation=45, ha="right")
    ax.set_ylabel(ylabel); ax.set_title(title); _subtitle(ax, subtitle)
    if pct: ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    if ylim: ax.set_ylim(*ylim)
    if len(ys) > 1: ax.legend(loc="upper left", ncols=len(ys))
    ax.set_xlim(-0.5, len(df) + 1.5)
    return fig


def grouped_bar(df: pd.DataFrame, cat: str, series: str, val: str, title: str, ylabel: str,
                subtitle: str | None = None, fmt: str = ",.0f", order=None, figsize=(10, 4.4)) -> plt.Figure:
    p = df.pivot(index=cat, columns=series, values=val)
    if order is not None: p = p.reindex(order)
    n = p.shape[1]
    w = 0.8 / n
    fig, ax = plt.subplots(figsize=figsize)
    xs = np.arange(len(p))
    for i, col in enumerate(p.columns):
        b = ax.bar(xs + (i - (n - 1) / 2) * w, p[col], width=w * 0.92, color=SERIES[i], label=str(col))
        for r, v in zip(b, p[col]):
            ax.text(r.get_x() + r.get_width() / 2, r.get_height(), _fmt(v, fmt), ha="center", va="bottom",
                    fontsize=7, color=INK["secondary"])
    ax.set_xticks(xs); ax.set_xticklabels(p.index, rotation=0)
    ax.set_ylabel(ylabel); ax.set_title(title); _subtitle(ax, subtitle)
    ax.legend(loc="upper left", ncols=n, bbox_to_anchor=(0, -0.10))
    return fig


def heatmap(m: pd.DataFrame, title: str, subtitle: str | None = None, xlabel: str = "", ylabel: str = "",
            figsize=(12, 4.2), cbar_label: str = "") -> plt.Figure:
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("seq", ["#f4f8fd"] + SEQUENTIAL)
    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(m.values, aspect="auto", cmap=cmap)
    ax.set_xticks(range(m.shape[1])); ax.set_xticklabels(m.columns)
    ax.set_yticks(range(m.shape[0])); ax.set_yticklabels(m.index)
    ax.grid(False); ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title); _subtitle(ax, subtitle)
    for s in ax.spines.values(): s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01); cb.outline.set_visible(False); cb.set_label(cbar_label)
    return fig


def scatter(df: pd.DataFrame, x: str, y: str, title: str, xlabel: str, ylabel: str, subtitle: str | None = None,
            size: str | None = None, label: str | None = None, label_top: int = 0, trend: bool = True,
            figsize=(8.5, 5.2)) -> plt.Figure:
    fig, ax = plt.subplots(figsize=figsize)
    s = 20 + 160 * (df[size] / df[size].max()) if size else 40
    ax.scatter(df[x], df[y], s=s, color=PRIMARY, alpha=0.7, edgecolor=INK["surface"], linewidth=1.5)
    if trend and len(df) > 2:
        k, b = np.polyfit(df[x], df[y], 1)
        xx = np.linspace(df[x].min(), df[x].max(), 50)
        ax.plot(xx, k * xx + b, color=INK["muted"], lw=1.2, ls="--")
    if label and label_top:
        for _, r in df.nsmallest(label_top, y).iterrows():
            ax.annotate(r[label], (r[x], r[y]), xytext=(5, -4), textcoords="offset points", fontsize=7.5,
                        color=INK["secondary"])
    ax.grid(axis="x"); ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title); _subtitle(ax, subtitle)
    return fig


def boxplot(groups: dict[str, pd.Series], title: str, ylabel: str, subtitle: str | None = None,
            log: bool = False, ref: dict[str, float] | None = None, figsize=(9, 4.4)) -> plt.Figure:
    fig, ax = plt.subplots(figsize=figsize)
    names = list(groups)
    bp = ax.boxplot([groups[k].dropna() for k in names], tick_labels=names, showfliers=False, patch_artist=True,
                    widths=0.5, medianprops=dict(color=INK["primary"], lw=1.6))
    for p in bp["boxes"]:
        p.set_facecolor("#cde2fb"); p.set_edgecolor(PRIMARY)
    for k in ("whiskers", "caps"):
        for l in bp[k]: l.set_color(PRIMARY)
    if ref:
        for i, n in enumerate(names, start=1):
            if n in ref:
                ax.hlines(ref[n], i - 0.3, i + 0.3, color=STATUS["critical"], lw=1.6, ls="--")
        ax.plot([], [], color=STATUS["critical"], ls="--", label="SLA target")
        ax.legend(loc="upper right")
    if log: ax.set_yscale("log")
    ax.set_ylabel(ylabel); ax.set_title(title); _subtitle(ax, subtitle)
    return fig


def two_state_bar(df: pd.DataFrame, cat: str, good: str, bad: str, title: str, subtitle: str | None = None,
                  good_label: str = "Within SLA", bad_label: str = "Breached", figsize=(9, None)) -> plt.Figure:
    """100% horizontal bars with reserved status colours (good vs critical)."""
    d = df.copy()
    tot = d[good] + d[bad]
    d["g"] = d[good] / tot * 100; d["b"] = d[bad] / tot * 100
    d = d.sort_values("g")
    h = figsize[1] or max(3.0, 0.45 * len(d) + 1.4)
    fig, ax = plt.subplots(figsize=(figsize[0], h))
    ax.barh(d[cat], d.g, color=STATUS["good"], height=0.6, label=good_label)
    ax.barh(d[cat], d.b, left=d.g + 0.4, color=STATUS["critical"], height=0.6, label=bad_label)
    for i, (gv, bv) in enumerate(zip(d.g, d.b)):
        ax.text(gv - 1, i, f"{gv:.1f}%", ha="right", va="center", color="white", fontsize=8.5, fontweight="bold")
        ax.text(100.5, i, f"{bv:.1f}%", ha="left", va="center", color=INK["secondary"], fontsize=8.5)
    ax.set_xlim(0, 108); ax.grid(False); ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    ax.set_title(title); _subtitle(ax, subtitle)
    ax.legend(loc="upper left", ncols=2, bbox_to_anchor=(0, -0.02))
    return fig
