"""Tests for src.clean on a small frame shaped like the real data."""

import pandas as pd

from src.clean import clean_returns


def make_returns():
    d = pd.to_datetime(["2020-09-14", "2021-06-11", "2021-06-14", "2021-06-15"])
    return pd.DataFrame(
        {
            "EDV.L": [0.0, 0.0, -0.55, 0.01],    # stale, stale, fake jump, first real day
            "IAG.L": [-0.37, 0.01, 0.02, 0.03],  # rights issue day first
            "HSBA.L": 0.01,
        },
        index=d,
    )


def test_edv_returns_removed_up_to_listing_date():
    cleaned, _ = clean_returns(make_returns())
    edv = cleaned["EDV.L"]
    assert edv[:"2021-06-14"].isna().all()
    assert edv["2021-06-15"] == 0.01  # first reliable day is kept


def test_iag_rights_issue_day_removed_only():
    cleaned, _ = clean_returns(make_returns())
    iag = cleaned["IAG.L"]
    assert pd.isna(iag["2020-09-14"])
    assert iag.notna().sum() == 3


def test_other_stocks_untouched_and_input_unchanged():
    r = make_returns()
    original = r.copy()
    cleaned, _ = clean_returns(r)
    pd.testing.assert_series_equal(cleaned["HSBA.L"], r["HSBA.L"])
    pd.testing.assert_frame_equal(r, original)


def test_report_counts_removed_values():
    _, report = clean_returns(make_returns())
    counts = dict(zip(report["ticker"], report["values_removed"]))
    assert counts == {"EDV.L": 3, "IAG.L": 1}
