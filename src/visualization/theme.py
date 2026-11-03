"""Shared visual identity for matplotlib, Plotly, Streamlit and the Power BI theme.

Palette: a validated, colour-vision-deficiency-checked categorical order
(slots are assigned in fixed order, never cycled), a single-hue sequential
blue ramp, and reserved status colours (good / warning / critical).
"""
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
PRIMARY = SERIES[0]
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}
INK = {"primary": "#0b0b0b", "secondary": "#52514e", "muted": "#898781", "grid": "#e1e0d9",
       "axis": "#c3c2b7", "surface": "#fcfcfb", "page": "#f9f9f7"}
FONT = "DejaVu Sans"


def apply_matplotlib_theme() -> None:
    import matplotlib as mpl
    mpl.rcParams.update({
        "figure.facecolor": INK["surface"], "axes.facecolor": INK["surface"], "savefig.facecolor": INK["surface"],
        "font.family": FONT, "font.size": 10, "axes.titlesize": 13, "axes.titleweight": "bold",
        "axes.titlelocation": "left", "axes.titlepad": 24, "axes.labelsize": 10,
        "axes.labelcolor": INK["secondary"], "axes.edgecolor": INK["axis"], "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "axes.grid.axis": "y",
        "grid.color": INK["grid"], "grid.linewidth": 0.6, "xtick.color": INK["muted"], "ytick.color": INK["muted"],
        "xtick.labelcolor": INK["secondary"], "ytick.labelcolor": INK["secondary"],
        "text.color": INK["primary"], "legend.frameon": False, "legend.fontsize": 9,
        "axes.prop_cycle": mpl.cycler(color=SERIES), "lines.linewidth": 2.0, "figure.dpi": 110,
    })


PLOTLY_LAYOUT = dict(
    font=dict(family="Inter, Segoe UI, system-ui, sans-serif", size=12, color=INK["primary"]),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    colorway=SERIES, margin=dict(l=10, r=10, t=48, b=10),
    xaxis=dict(showgrid=False, linecolor=INK["axis"], tickfont=dict(color=INK["secondary"])),
    yaxis=dict(gridcolor=INK["grid"], zeroline=False, tickfont=dict(color=INK["secondary"])),
    legend=dict(orientation="h", y=1.08, x=0, title_text=""),
    hoverlabel=dict(bgcolor="white", font_size=12),
    title=dict(x=0, xanchor="left", font=dict(size=15)),
)
