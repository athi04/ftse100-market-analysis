"""Tests for src.metrics using small hand built series with known answers."""

import numpy as np
import pandas as pd
import pytest

from src.metrics import (
    annualised_return,
    annualised_volatility,
    drawdown,
    log_returns,
    max_drawdown,
    rolling_volatility,
    sector_returns,
)

SQRT_252 = np.sqrt(252)


def dates(n):
    return pd.date_range("2024-01-01", periods=n, freq="B")


# Returns and volatility

def test_constant_prices_give_zero_returns_and_volatility():
    prices = pd.Series(100.0, index=dates(40))
    r = log_returns(prices)
    assert (r == 0).all()
    assert annualised_volatility(r) == 0
    assert (rolling_volatility(r, window=30).dropna() == 0).all()


def test_log_returns_known_values():
    prices = pd.Series([100.0, 110.0, 99.0], index=dates(3))
    r = log_returns(prices)
    assert len(r) == 2  # first day has no previous price
    assert r.iloc[0] == pytest.approx(np.log(1.1))
    assert r.iloc[1] == pytest.approx(np.log(0.9))


def test_rolling_volatility_known_value():
    # Sample std of [0.01, -0.01] is 0.02 / sqrt(2)
    r = pd.Series([0.01, -0.01, 0.01], index=dates(3))
    vol = rolling_volatility(r, window=2)
    assert np.isnan(vol.iloc[0])  # not enough data for a full window
    assert vol.iloc[1] == pytest.approx(0.02 / np.sqrt(2) * SQRT_252)


def test_annualised_return_recovers_known_growth():
    # 252 equal daily log returns that compound to exactly 10% growth
    r = pd.Series(np.log(1.10) / 252, index=dates(252))
    assert annualised_return(r) == pytest.approx(0.10)


# Drawdowns

def test_drawdown_known_path():
    prices = pd.Series([100.0, 120.0, 90.0, 108.0, 130.0], index=dates(5))
    expected = [0.0, 0.0, -0.25, -0.10, 0.0]
    assert drawdown(prices).tolist() == pytest.approx(expected)


def test_max_drawdown_with_recovery():
    d = dates(5)
    prices = pd.Series([100.0, 120.0, 90.0, 108.0, 130.0], index=d)
    result = max_drawdown(prices)
    assert result["depth"] == pytest.approx(-0.25)
    assert result["peak_date"] == d[1]
    assert result["trough_date"] == d[2]
    assert result["recovery_date"] == d[4]  # first close back above 120


def test_max_drawdown_not_recovered():
    prices = pd.Series([100.0, 80.0, 90.0], index=dates(3))
    result = max_drawdown(prices)
    assert result["depth"] == pytest.approx(-0.20)
    assert result["recovery_date"] is None


def test_max_drawdown_rising_prices_is_zero():
    prices = pd.Series([100.0, 101.0, 102.0], index=dates(3))
    assert max_drawdown(prices)["depth"] == 0


# Sector aggregation

CONSTITUENTS = pd.DataFrame({
    "ticker": ["A1", "A2", "B1"],
    "sector": ["Alpha", "Alpha", "Beta"],
})


def test_sector_returns_equal_weighted_average():
    # Alpha: one stock up 10%, one down 10%, so an equal split earns 0%
    # Beta: a single stock, so the sector return is just that stock's return
    simple = pd.DataFrame({"A1": [0.10], "A2": [-0.10], "B1": [0.05]}, index=dates(1))
    out = sector_returns(np.log1p(simple), CONSTITUENTS)
    assert out.loc[dates(1)[0], "Alpha"] == pytest.approx(0.0)
    assert out.loc[dates(1)[0], "Beta"] == pytest.approx(np.log(1.05))


def test_sector_returns_ignores_missing_stocks():
    # A2 has no price yet (for example not listed), so Alpha uses A1 alone
    simple = pd.DataFrame({"A1": [0.04], "A2": [np.nan], "B1": [0.0]}, index=dates(1))
    out = sector_returns(np.log1p(simple), CONSTITUENTS)
    assert out.iloc[0]["Alpha"] == pytest.approx(np.log(1.04))


def test_sector_returns_rejects_unknown_ticker():
    r = pd.DataFrame({"A1": [0.0], "ZZZ": [0.0]}, index=dates(1))
    with pytest.raises(ValueError, match="ZZZ"):
        sector_returns(r, CONSTITUENTS)
