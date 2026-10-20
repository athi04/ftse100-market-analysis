"""Streamlit page for exploring each FTSE 100 sector.

Run from the project root, after downloading the data with python -m src.fetch:

    streamlit run app.py

It uses the same cleaning, metrics and end date as the notebook, so the
numbers match it.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from src import plots
from src.clean import clean_returns
from src.metrics import (
    annualised_return, annualised_volatility, drawdown, log_returns,
    max_drawdown, rolling_volatility, sector_returns,
)

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
ANALYSIS_END = "2026-10-19"  # same fixed end date as the notebook


@st.cache_data
def load():
    """Load prices, clean returns and build equal weighted sector returns once."""
    prices = pd.read_csv(RAW / "constituents_prices.csv", index_col=0, parse_dates=True)
    prices = prices.loc[:ANALYSIS_END]
    constituents = pd.read_csv(ROOT / "data" / "constituents.csv")
    returns, _ = clean_returns(log_returns(prices))
    return prices.index[0], returns, constituents, sector_returns(returns, constituents)


def sector_level(daily, start_date):
    """Turn daily log returns into a level that starts at 100.

    Equal weighted sectors are not traded, so they have no real price. Summing
    log returns and exponentiating gives the growth of 100 invested at the start.
    """
    level = 100 * np.exp(daily.cumsum())
    start = pd.Series([100.0], index=[start_date])
    return pd.concat([start, level])


def fmt(date):
    """Format a date as '6 January 2023'."""
    return f"{date.day} {date:%B %Y}"


st.set_page_config(page_title="FTSE 100 sectors", layout="wide")
st.title("FTSE 100 sectors since 2019")

if not (RAW / "constituents_prices.csv").exists():
    st.error("No price data found. Run `python -m src.fetch` from the project root first.")
    st.stop()

plots.use_style()
start_date, returns, constituents, sectors = load()

sector = st.selectbox("Sector", sorted(sectors.columns))
daily = sectors[sector].dropna()
level = sector_level(daily, start_date)
worst = max_drawdown(level)
members = constituents[constituents["sector"] == sector]

st.caption(
    f"Equal weighted: each of the {len(members)} stocks counts the same, and returns "
    f"include dividends. The level shows the growth of 100 invested at the close on "
    f"{fmt(start_date)}. Data from Yahoo Finance to {fmt(daily.index[-1])}."
)

# Headline numbers
c1, c2, c3, c4 = st.columns(4)
c1.metric("Annualised return", f"{annualised_return(daily):.1%}")
c2.metric("Annualised volatility", f"{annualised_volatility(daily):.1%}")
c3.metric("Worst drawdown", f"{worst['depth']:.1%}")
c4.metric("Stocks", len(members))

if worst["recovery_date"] is None:
    st.write(f"The worst fall bottomed on {fmt(worst['trough_date'])} and the sector "
             f"has not yet recovered its {worst['peak_date']:%B %Y} high.")
else:
    st.write(f"The worst fall bottomed on {fmt(worst['trough_date'])} and recovered its "
             f"{worst['peak_date']:%B %Y} high on {fmt(worst['recovery_date'])}.")

# Charts
vol = rolling_volatility(daily, window=30)
for fig in (
    plots.plot_index(level, daily, title=f"{sector}: growth of 100"),
    plots.plot_volatility(vol, events=[], median=vol.median(),
                          title=f"{sector}: rolling 30 day volatility, annualised"),
    plots.plot_drawdown(drawdown(level), worst, title=f"{sector}: fall from previous peak",
                       label_recovery=False),
):
    st.pyplot(fig)
    plt.close(fig)

# The stocks behind the sector
st.subheader("Stocks in this sector")
stock_returns = returns[members["ticker"]]
table = members.set_index("ticker")[["company"]].assign(
    first_date=stock_returns.apply(pd.Series.first_valid_index).dt.date,
    annualised_return=annualised_return(stock_returns),
    annualised_volatility=annualised_volatility(stock_returns),
).sort_values("annualised_volatility")
st.dataframe(
    table.style.format({"annualised_return": "{:.1%}", "annualised_volatility": "{:.1%}"}),
    width="stretch",
)
