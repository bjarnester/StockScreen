"""Trailing Twelve Months (TTM) calculations from quarterly data."""

from typing import Optional
from datetime import datetime
import pandas as pd


class TTMCalculator:
    """Calculates TTM metrics from quarterly financial data."""

    def __init__(self, financial_data: dict):
        """
        Initialize with financial data dict from FinancialFetcher.

        Args:
            financial_data: Dict containing quarterly_financials, quarterly_cashflow, etc.
        """
        self.data = financial_data
        self._quarterly_financials = self._parse_quarterly(financial_data.get("quarterly_financials"))
        self._quarterly_cashflow = self._parse_quarterly(financial_data.get("quarterly_cashflow"))
        self._quarterly_balance = self._parse_quarterly(financial_data.get("quarterly_balance"))

    def _parse_quarterly(self, data: Optional[dict]) -> Optional[pd.DataFrame]:
        """Convert quarterly dict data back to DataFrame sorted by date."""
        if not data:
            return None

        try:
            df = pd.DataFrame(data)
            df.columns = pd.to_datetime(df.columns)
            df = df.sort_index(axis=1, ascending=False)  # Most recent first
            return df
        except Exception:
            return None

    def _get_last_n_quarters(self, df: Optional[pd.DataFrame], n: int = 4) -> Optional[pd.DataFrame]:
        """Get the last n quarters of data."""
        if df is None or df.empty:
            return None

        if df.shape[1] < n:
            return None

        return df.iloc[:, :n]

    def _sum_quarters(self, df: Optional[pd.DataFrame], field: str, n: int = 4) -> Optional[float]:
        """Sum a field across n quarters."""
        quarters = self._get_last_n_quarters(df, n)
        if quarters is None:
            return None

        if field not in quarters.index:
            return None

        values = quarters.loc[field].dropna()
        if len(values) < n:
            return None

        return float(values.sum())

    def get_ttm_revenue(self) -> Optional[float]:
        """Calculate TTM revenue."""
        return self._sum_quarters(
            self._quarterly_financials,
            "Total Revenue"
        )

    def get_ttm_net_income(self) -> Optional[float]:
        """Calculate TTM net income."""
        return self._sum_quarters(
            self._quarterly_financials,
            "Net Income"
        )

    def get_ttm_operating_income(self) -> Optional[float]:
        """Calculate TTM operating income (EBIT)."""
        return self._sum_quarters(
            self._quarterly_financials,
            "Operating Income"
        ) or self._sum_quarters(
            self._quarterly_financials,
            "EBIT"
        )

    def get_ttm_operating_cashflow(self) -> Optional[float]:
        """Calculate TTM operating cash flow."""
        return self._sum_quarters(
            self._quarterly_cashflow,
            "Operating Cash Flow"
        ) or self._sum_quarters(
            self._quarterly_cashflow,
            "Cash Flow From Continuing Operating Activities"
        )

    def get_ttm_capex(self) -> Optional[float]:
        """Calculate TTM capital expenditures."""
        return self._sum_quarters(
            self._quarterly_cashflow,
            "Capital Expenditure"
        )

    def get_ttm_fcf(self) -> Optional[float]:
        """Calculate TTM free cash flow (Operating CF - CapEx)."""
        # Try direct FCF first
        direct_fcf = self._sum_quarters(
            self._quarterly_cashflow,
            "Free Cash Flow"
        )
        if direct_fcf is not None:
            return direct_fcf

        # Calculate from components
        ocf = self.get_ttm_operating_cashflow()
        capex = self.get_ttm_capex()

        if ocf is None:
            return None

        if capex is None:
            return ocf  # Assume no CapEx if not reported

        # CapEx is typically negative, so we add it
        if capex < 0:
            return ocf + capex
        else:
            return ocf - capex

    def get_latest_balance_sheet_item(self, field: str) -> Optional[float]:
        """Get the most recent balance sheet item."""
        if self._quarterly_balance is None or self._quarterly_balance.empty:
            return None

        if field not in self._quarterly_balance.index:
            return None

        # Get first non-null value (most recent)
        values = self._quarterly_balance.loc[field].dropna()
        if values.empty:
            return None

        return float(values.iloc[0])

    def get_all_ttm_metrics(self) -> dict:
        """Get all TTM metrics as a dict."""
        return {
            "ttm_revenue": self.get_ttm_revenue(),
            "ttm_net_income": self.get_ttm_net_income(),
            "ttm_operating_income": self.get_ttm_operating_income(),
            "ttm_operating_cashflow": self.get_ttm_operating_cashflow(),
            "ttm_capex": self.get_ttm_capex(),
            "ttm_fcf": self.get_ttm_fcf(),
        }
