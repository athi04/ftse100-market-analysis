"""Remove known bad values from constituent daily returns.

Each rule fixes a specific, documented problem in the Yahoo data. Bad returns
are set to NaN rather than replaced with a guess, so the affected stock simply
drops out of its sector average on those days. The rules and the number of
values each one removes are reported in the README.
"""

import pandas as pd

# Endeavour Mining's London line traded very thinly before its main listing
# moved to London on 14 June 2021. Before then the price is unchanged on most
# days, which creates fake jumps (+34% on 2019-08-12, -55% on 2021-06-14).
# All returns up to and including 14 June 2021 are removed.
STALE_UNTIL = {"EDV.L": "2021-06-14"}

# IAG's price falls 37% on 14 September 2020 around its rights issue, and
# Yahoo has not adjusted for it. Holders did not lose 37%, so the return on
# that day is removed.
BAD_DAYS = {"IAG.L": ["2020-09-14"]}


def clean_returns(returns: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the cleaning rules to a frame of daily returns (one column per stock).

    Returns (cleaned, report). `cleaned` is a copy with bad values set to NaN.
    `report` has one row per rule with the number of values it removed.
    The input is not changed.
    """
    cleaned = returns.copy()
    report = []

    for ticker, last_bad in STALE_UNTIL.items():
        if ticker in cleaned:
            mask = cleaned.index <= pd.Timestamp(last_bad)
            removed = int(cleaned.loc[mask, ticker].notna().sum())
            cleaned.loc[mask, ticker] = float("nan")
            report.append((ticker, f"stale prices up to {last_bad}", removed))

    for ticker, days in BAD_DAYS.items():
        if ticker in cleaned:
            idx = cleaned.index.intersection(pd.to_datetime(days))
            removed = int(cleaned.loc[idx, ticker].notna().sum())
            cleaned.loc[idx, ticker] = float("nan")
            report.append((ticker, f"unadjusted rights issue on {', '.join(days)}", removed))

    return cleaned, pd.DataFrame(report, columns=["ticker", "rule", "values_removed"])
