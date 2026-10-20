"""Return, risk and sector metrics for daily price data.

All functions are pure: they take pandas objects and return new ones without
changing their inputs. Prices are a Series (one asset) or a DataFrame (one
column per asset) with a date index. Returns are daily log returns.
"""

import numpy as np
import pandas as pd

TRADING_DAYS = 252  # conventional number of trading days in a year


def log_returns(prices):
    """Daily log returns, ln(P_t / P_{t-1}).

    Log returns add up over time, which makes them convenient for volatility
    and aggregation. The first row is dropped because it has no previous price.
    Gaps (for example before a company listed) stay as NaN.
    """
    return np.log(prices).diff().iloc[1:]


def rolling_volatility(returns, window=30):
    """Rolling standard deviation of returns, annualised by sqrt(252).

    `window` is in trading days. Daily volatility is scaled by sqrt(252)
    because, for independent daily returns, variance grows linearly with time.
    The first `window - 1` values are NaN.
    """
    return returns.rolling(window).std() * np.sqrt(TRADING_DAYS)


def annualised_volatility(returns):
    """Standard deviation of daily returns over the whole period, times sqrt(252)."""
    return returns.std() * np.sqrt(TRADING_DAYS)


def annualised_return(returns):
    """Compound annual growth rate implied by daily log returns.

    The mean daily log return times 252 is the annual log return; exp(x) - 1
    turns it into an ordinary percentage growth rate. NaNs are skipped, so each
    asset is measured over the days it has data.
    """
    return np.exp(returns.mean() * TRADING_DAYS) - 1


def drawdown(prices):
    """Fall from the running peak, as a fraction (0 at a peak, -0.25 is 25% below)."""
    return prices / prices.cummax() - 1


def max_drawdown(prices):
    """Worst drawdown of a single price series and how it played out.

    Returns a dict with:
        depth          worst drawdown as a fraction (for example -0.25)
        peak_date      date of the high before the fall
        trough_date    date of the lowest point
        recovery_date  first date the price got back to the peak, or None if
                       it has not recovered by the end of the data
    """
    prices = prices.dropna()
    dd = drawdown(prices)
    trough_date = dd.idxmin()
    depth = dd.loc[trough_date]

    if depth == 0:
        # Never fell below a previous high, so there is nothing to recover from
        return {"depth": 0.0, "peak_date": trough_date,
                "trough_date": trough_date, "recovery_date": trough_date}

    peak_date = prices.loc[:trough_date].idxmax()
    after = prices.loc[trough_date:]
    recovered = after[after >= prices.loc[peak_date]]
    recovery_date = recovered.index[0] if len(recovered) else None
    return {"depth": float(depth), "peak_date": peak_date,
            "trough_date": trough_date, "recovery_date": recovery_date}


def sector_returns(returns, constituents):
    """Equal weighted daily log return for each sector.

    This is NOT market cap weighted: every stock in a sector counts the same,
    so a small company moves its sector as much as a large one. Each day's
    figure is the return of holding an equal amount of every stock in the
    sector that has a price that day.

    Log returns are converted to simple returns before averaging, because a
    portfolio's simple return is the weighted average of its stocks' simple
    returns. The average is then converted back to a log return so it can be
    used with the other functions here.

    `constituents` needs `ticker` and `sector` columns. Every column of
    `returns` must appear in it.
    """
    sector_of = constituents.set_index("ticker")["sector"]
    unknown = [t for t in returns.columns if t not in sector_of.index]
    if unknown:
        raise ValueError(f"Tickers missing from constituents: {unknown}")

    simple = np.exp(returns) - 1
    # Group columns by sector; mean skips NaN, so it averages available stocks
    sector_simple = simple.T.groupby(sector_of.loc[simple.columns]).mean().T
    return np.log1p(sector_simple)
