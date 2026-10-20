"""Reusable matplotlib charts for the analysis notebook.

Each function draws one chart and returns the matplotlib Figure, so the
notebook decides whether to show it, save it, or both. Call use_style() once
before plotting to apply the shared look.
"""

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# Colours: one blue for data, neutral greys for everything else
BLUE = "#2a78d6"
BLUE_LIGHT = "#cde2fb"
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

# Single hue sequential ramp (light to dark blue) for the correlation heatmap
BLUE_RAMP = LinearSegmentedColormap.from_list(
    "blue_ramp",
    ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"],
)


def use_style():
    """Apply a clean, consistent style to every chart."""
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "figure.dpi": 110,
        "savefig.dpi": 150,
        "font.family": "sans-serif",
        "font.size": 10,
        "text.color": INK,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.labelcolor": INK_SECONDARY,
        "axes.edgecolor": AXIS,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,
        "xtick.labelcolor": INK_SECONDARY,
        "ytick.labelcolor": INK_SECONDARY,
        "lines.linewidth": 1.5,
        "legend.frameon": False,
    })


def _percent_axis(ax, decimals=0):
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.{decimals}%}"))


def _day(date):
    """Format a date as '6 Jan 2023' (no leading zero, works on every OS)."""
    return f"{date.day} {date:%b %Y}"


def _note(ax, x, y, text, xytext, ha="left"):
    """Label a point with a short note and a thin leader line."""
    ax.annotate(
        text, xy=(x, y), xytext=xytext, textcoords="offset points",
        ha=ha, fontsize=9, color=INK_SECONDARY,
        arrowprops=dict(arrowstyle="-", color=INK_MUTED, lw=0.8),
    )


def plot_index(prices, returns):
    """Index level on top, daily log returns underneath, sharing the date axis."""
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(10, 6), sharex=True, gridspec_kw={"height_ratios": [2, 1]}
    )
    top.plot(prices.index, prices, color=BLUE)
    top.set_title("FTSE 100 index level")
    top.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))

    bottom.plot(returns.index, returns, color=BLUE, lw=0.6)
    bottom.axhline(0, color=AXIS, lw=0.8)
    bottom.set_title("Daily log return")
    _percent_axis(bottom)
    fig.tight_layout()
    return fig


def plot_volatility(vol, events, median=None):
    """Rolling annualised volatility with labelled events.

    `events` is a list of (date, label, (dx, dy)) where (dx, dy) is the label
    offset in points from the point on the line.
    """
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(vol.index, vol, color=BLUE)
    if median is not None:
        ax.axhline(median, color=INK_MUTED, lw=0.8, ls="--")
        # Label sits just outside the right edge so it never covers the line
        ax.text(1.005, median, f"median\n{median:.0%}", transform=ax.get_yaxis_transform(),
                va="center", ha="left", fontsize=9, color=INK_MUTED)
    for date, label, offset in events:
        _note(ax, date, vol.loc[date], label, offset)
    ax.set_title("FTSE 100: rolling 30 day volatility, annualised")
    ax.set_ylim(0, None)
    _percent_axis(ax)
    fig.tight_layout()
    return fig


def plot_drawdown(dd, worst):
    """Drawdown from running peak, with the worst fall and its recovery marked.

    `worst` is the dict returned by metrics.max_drawdown.
    """
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.fill_between(dd.index, dd, 0, color=BLUE_LIGHT, lw=0)
    ax.plot(dd.index, dd, color=BLUE, lw=1.2)
    ax.axhline(0, color=AXIS, lw=0.8)

    trough = worst["trough_date"]
    _note(ax, trough, worst["depth"],
          f"Worst: {worst['depth']:.1%} on {_day(trough)}", (15, -5))
    if worst["recovery_date"] is not None:
        rec = worst["recovery_date"]
        # Label placed low and to the left, in the empty area under the 2022 curve
        _note(ax, rec, 0, f"Back to the {worst['peak_date']:%b %Y} high\non {_day(rec)}",
              (-70, -120), ha="center")
    ax.set_title("FTSE 100: fall from previous peak")
    _percent_axis(ax)
    fig.tight_layout()
    return fig


def plot_sector_risk_return(table, offsets=None):
    """Scatter of annualised volatility against annualised return, one dot per sector.

    `table` has a sector index and `ann_return` and `ann_vol` columns.
    `offsets` optionally maps a sector to a label offset in points.
    """
    offsets = offsets or {}
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(table["ann_vol"], table["ann_return"], s=60, color=BLUE,
               edgecolor=SURFACE, linewidth=1.5, zorder=3)
    for sector, row in table.iterrows():
        dx, dy = offsets.get(sector, (7, -3))
        ax.annotate(sector, (row["ann_vol"], row["ann_return"]),
                    xytext=(dx, dy), textcoords="offset points",
                    ha="left" if dx >= 0 else "right", fontsize=9, color=INK_SECONDARY)
    ax.grid(axis="x")
    ax.set_xlabel("Annualised volatility (risk)")
    ax.set_ylabel("Annualised return")
    ax.set_title("Sectors: return against risk (equal weighted, since 2019)")
    ax.xaxis.set_major_locator(plt.MultipleLocator(0.05))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    _percent_axis(ax)
    fig.tight_layout()
    return fig


def plot_correlation(corr):
    """Heatmap of a correlation matrix with the value printed in each cell."""
    n = len(corr)
    fig, ax = plt.subplots(figsize=(9, 7.5))
    im = ax.imshow(corr.values, cmap=BLUE_RAMP, vmin=0, vmax=1)
    ax.grid(False)
    ax.set_xticks(range(n), corr.columns, rotation=45, ha="right")
    ax.set_yticks(range(n), corr.index)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for i in range(n):
        for j in range(n):
            v = corr.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if v > 0.6 else INK)
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(color=INK_MUTED, labelcolor=INK_SECONDARY)
    ax.set_title("Correlation of daily sector returns")
    fig.tight_layout()
    return fig
