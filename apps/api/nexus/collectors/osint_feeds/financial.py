"""Financial data fetchers -- defense stocks and oil prices.

Ported from Shadowbroker financial.py to async NEXUS patterns.
Uses asyncio.to_thread() to wrap synchronous yfinance calls.
"""

from __future__ import annotations

import asyncio

import structlog
import yfinance as yf

logger = structlog.get_logger("nexus.collectors.osint_feeds.financial")


def _fetch_single_ticker(symbol: str, period: str = "2d") -> tuple[str, dict | None]:
    """Fetch a single yfinance ticker synchronously.

    Returns ``(symbol, data_dict)`` or ``(symbol, None)`` on failure.
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        if len(hist) >= 1:
            current_price = hist["Close"].iloc[-1]
            prev_close = hist["Close"].iloc[0] if len(hist) > 1 else current_price
            change_percent = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0
            return symbol, {
                "price": round(float(current_price), 2),
                "change_percent": round(float(change_percent), 2),
                "up": bool(change_percent >= 0),
            }
    except Exception as exc:
        logger.warning("could not fetch ticker", symbol=symbol, error=str(exc))
    return symbol, None


async def fetch_defense_stocks() -> dict:
    """Fetch current price and daily change for major defense/intel tickers.

    Tickers: RTX, LMT, NOC, GD, BA, PLTR.
    """
    tickers = ["RTX", "LMT", "NOC", "GD", "BA", "PLTR"]
    stocks: dict[str, dict] = {}
    try:
        tasks = [asyncio.to_thread(_fetch_single_ticker, t, "2d") for t in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.warning("ticker fetch failed", error=str(result))
                continue
            symbol, data = result
            if data is not None:
                stocks[symbol] = data
        logger.info("defense stocks fetched", count=len(stocks))
    except Exception as exc:
        logger.error("error fetching defense stocks", error=str(exc))
    return stocks


async def fetch_oil_prices() -> dict:
    """Fetch current WTI and Brent crude oil prices."""
    ticker_map = {"WTI Crude": "CL=F", "Brent Crude": "BZ=F"}
    oil: dict[str, dict] = {}
    try:
        tasks = [asyncio.to_thread(_fetch_single_ticker, sym, "5d") for sym in ticker_map.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for name, result in zip(ticker_map.keys(), results):
            if isinstance(result, Exception):
                logger.warning("oil ticker fetch failed", name=name, error=str(result))
                continue
            _symbol, data = result
            if data is not None:
                oil[name] = data
        logger.info("oil prices fetched", count=len(oil))
    except Exception as exc:
        logger.error("error fetching oil prices", error=str(exc))
    return oil
