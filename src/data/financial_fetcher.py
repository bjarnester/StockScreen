"""Fetches financial data from yfinance with rate limiting and caching."""

import time
from typing import Optional
import yfinance as yf
import pandas as pd
from ratelimit import limits, sleep_and_retry
from rich.console import Console

from ..config import settings
from .cache_manager import cache

console = Console()


class FinancialFetcher:
    """Fetches financial data from yfinance with rate limiting."""

    def __init__(self):
        self.calls_per_minute = settings.rate_limit.calls_per_minute

    @sleep_and_retry
    @limits(calls=30, period=60)
    def _rate_limited_fetch(self, ticker: str) -> Optional[yf.Ticker]:
        """Fetch ticker with rate limiting."""
        try:
            return yf.Ticker(ticker)
        except Exception as e:
            console.print(f"[red]Error fetching {ticker}: {e}[/red]")
            return None

    def fetch_financials(self, ticker: str, force_refresh: bool = False) -> Optional[dict]:
        """
        Fetch all financial data for a ticker.

        Returns dict with:
        - info: Company info (sector, industry, market cap, etc.)
        - quarterly_financials: Quarterly income statement
        - annual_financials: Annual income statement
        - quarterly_balance: Quarterly balance sheet
        - annual_balance: Annual balance sheet
        - quarterly_cashflow: Quarterly cash flow
        - annual_cashflow: Annual cash flow
        """
        if not force_refresh:
            cached = cache.get_financials(ticker)
            if cached:
                return cached

        stock = self._rate_limited_fetch(ticker)
        if not stock:
            return None

        try:
            data = {
                "ticker": ticker,
                "info": self._safe_get_info(stock),
                "quarterly_financials": self._df_to_dict(stock.quarterly_income_stmt),
                "annual_financials": self._df_to_dict(stock.income_stmt),
                "quarterly_balance": self._df_to_dict(stock.quarterly_balance_sheet),
                "annual_balance": self._df_to_dict(stock.balance_sheet),
                "quarterly_cashflow": self._df_to_dict(stock.quarterly_cashflow),
                "annual_cashflow": self._df_to_dict(stock.cashflow),
            }

            # Only cache if we got meaningful data
            if data["info"] and (data["annual_financials"] or data["quarterly_financials"]):
                cache.set_financials(ticker, data)
                return data

            return None

        except Exception as e:
            console.print(f"[red]Error processing {ticker}: {e}[/red]")
            return None

    def _safe_get_info(self, stock: yf.Ticker) -> dict:
        """Safely get stock info, handling errors."""
        try:
            info = stock.info
            if isinstance(info, dict):
                return {
                    "symbol": info.get("symbol"),
                    "shortName": info.get("shortName"),
                    "longName": info.get("longName"),
                    "sector": info.get("sector"),
                    "industry": info.get("industry"),
                    "marketCap": info.get("marketCap"),
                    "trailingPE": info.get("trailingPE"),
                    "forwardPE": info.get("forwardPE"),
                    "currentPrice": info.get("currentPrice") or info.get("regularMarketPrice"),
                    "currency": info.get("currency"),
                    "country": info.get("country"),
                }
            return {}
        except Exception:
            return {}

    def _df_to_dict(self, df: Optional[pd.DataFrame]) -> Optional[dict]:
        """Convert DataFrame to serializable dict."""
        if df is None or df.empty:
            return None

        try:
            # Convert index (dates) to strings
            result = {}
            for col in df.columns:
                col_str = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)
                result[col_str] = {}
                for idx in df.index:
                    val = df.loc[idx, col]
                    if pd.notna(val):
                        result[col_str][idx] = float(val) if isinstance(val, (int, float)) else val
            return result
        except Exception:
            return None

    def fetch_batch(self, tickers: list[str], progress_callback=None) -> dict[str, dict]:
        """
        Fetch financial data for multiple tickers.

        Args:
            tickers: List of ticker symbols
            progress_callback: Optional callback(current, total) for progress updates

        Returns:
            Dict mapping ticker to financial data
        """
        results = {}
        total = len(tickers)

        for i, ticker in enumerate(tickers):
            if progress_callback:
                progress_callback(i + 1, total)

            data = self.fetch_financials(ticker)
            if data:
                results[ticker] = data

        return results
