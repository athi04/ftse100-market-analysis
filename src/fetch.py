"""Download daily FTSE 100 index and constituent prices from Yahoo Finance.

Run from the project root with:

    python -m src.fetch

Prices are adjusted closes (auto_adjust=True), so they account for splits and
dividends. Files are written to data/raw/, which is not committed to git.
"""

import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
CONSTITUENTS_FILE = ROOT / "data" / "constituents.csv"
RAW_DIR = ROOT / "data" / "raw"

INDEX_TICKER = "^FTSE"
START_DATE = "2019-01-01"

log = logging.getLogger(__name__)


def default_end_date() -> str:
    """Today's date in London.

    yfinance treats `end` as exclusive, so using today means the data stops at
    the last completed trading day and never includes a half finished session.
    """
    return datetime.now(ZoneInfo("Europe/London")).strftime("%Y-%m-%d")


def _download_close(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """Download adjusted close prices, one column per ticker.

    Returns an empty frame if the request itself fails.
    """
    try:
        data = yf.download(
            tickers,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as exc:  # network errors, Yahoo rate limits, etc.
        log.warning("Download failed for %s: %s", tickers, exc)
        return pd.DataFrame()
    if data.empty:
        return pd.DataFrame()
    close = data["Close"]
    # A single ticker can come back as a Series; make it a one column frame
    if isinstance(close, pd.Series):
        close = close.to_frame(tickers[0])
    return close


def _missing(prices: pd.DataFrame, tickers: list[str]) -> list[str]:
    """Tickers with no column, or a column with no prices at all."""
    return [t for t in tickers if t not in prices or prices[t].isna().all()]


def fetch_prices(
    tickers: list[str], start: str = START_DATE, end: str | None = None
) -> tuple[pd.DataFrame, list[str]]:
    """Download adjusted closes for `tickers`, retrying each failure once.

    Returns (prices, failed) where prices has a date index and one column per
    successful ticker, and failed lists tickers that failed twice.
    """
    end = end or default_end_date()

    # First attempt: one batch request for everything
    prices = _download_close(tickers, start, end)
    prices = prices.drop(columns=_missing(prices, list(prices.columns)))

    # Second attempt: retry each missing ticker on its own
    failed = []
    for ticker in _missing(prices, tickers):
        log.info("Retrying %s", ticker)
        retry = _download_close([ticker], start, end)
        if _missing(retry, [ticker]):
            log.warning("Skipping %s: no data after retry", ticker)
            failed.append(ticker)
        else:
            prices = prices.join(retry[[ticker]], how="outer")

    # Keep the original ticker order and drop rows where nothing traded
    ok = [t for t in tickers if t not in failed]
    prices = prices[ok].dropna(how="all").sort_index()
    prices.index.name = "Date"
    return prices, failed


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    end = default_end_date()

    constituents = pd.read_csv(CONSTITUENTS_FILE)
    tickers = constituents["ticker"].tolist()

    index_prices, index_failed = fetch_prices([INDEX_TICKER], end=end)
    if index_failed:
        raise SystemExit(f"Could not download the index {INDEX_TICKER}; stopping.")
    stock_prices, failed = fetch_prices(tickers, end=end)

    index_prices.to_csv(RAW_DIR / "ftse100_index.csv")
    stock_prices.to_csv(RAW_DIR / "constituents_prices.csv")
    (RAW_DIR / "failed_tickers.txt").write_text("\n".join(failed) + ("\n" if failed else ""))

    log.info(
        "Index: %d days, %s to %s",
        len(index_prices), index_prices.index.min().date(), index_prices.index.max().date(),
    )
    log.info("Constituents: %d of %d downloaded", stock_prices.shape[1], len(tickers))
    log.info("Failed tickers: %s", ", ".join(failed) if failed else "none")
    log.info("Saved to %s", RAW_DIR)


if __name__ == "__main__":
    main()
