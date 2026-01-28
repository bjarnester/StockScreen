"""Core financial metrics calculations."""

from typing import Optional
from dataclasses import dataclass
import pandas as pd

from .ttm_calculator import TTMCalculator


@dataclass
class FinancialMetrics:
    """Container for calculated financial metrics."""
    ticker: str
    name: str
    exchange: str
    sector: Optional[str]
    industry: Optional[str]

    # Valuation
    pe_ratio: Optional[float] = None
    market_cap: Optional[float] = None

    # Profitability
    roic: Optional[float] = None
    roic_history: Optional[list[float]] = None

    # Growth
    revenue_growth_years: Optional[int] = None
    earnings_growth_years: Optional[int] = None

    # Financial Health
    debt_to_equity: Optional[float] = None
    free_cash_flow: Optional[float] = None
    cf_yield: Optional[float] = None  # FCF / Revenue

    # TTM values
    ttm_revenue: Optional[float] = None
    ttm_earnings: Optional[float] = None

    # Flags
    has_positive_earnings: bool = False
    data_complete: bool = False


class MetricsCalculator:
    """Calculates financial metrics from raw data."""

    def __init__(self, financial_data: dict, company_info: dict):
        """
        Initialize calculator.

        Args:
            financial_data: Dict from FinancialFetcher
            company_info: Company dict with symbol, name, exchange, ticker
        """
        self.data = financial_data
        self.company = company_info
        self.ttm = TTMCalculator(financial_data)

        # Parse annual data
        self._annual_financials = self._parse_annual(financial_data.get("annual_financials"))
        self._annual_balance = self._parse_annual(financial_data.get("annual_balance"))
        self._annual_cashflow = self._parse_annual(financial_data.get("annual_cashflow"))

    def _parse_annual(self, data: Optional[dict]) -> Optional[pd.DataFrame]:
        """Convert annual dict to DataFrame sorted by date."""
        if not data:
            return None

        try:
            df = pd.DataFrame(data)
            df.columns = pd.to_datetime(df.columns)
            df = df.sort_index(axis=1, ascending=False)
            return df
        except Exception:
            return None

    def calculate_pe_ratio(self) -> Optional[float]:
        """Calculate PE ratio from info or TTM earnings."""
        info = self.data.get("info", {})

        # Try direct PE from yfinance
        pe = info.get("trailingPE")
        if pe and pe > 0:
            return float(pe)

        # Calculate from market cap and TTM earnings
        market_cap = info.get("marketCap")
        ttm_earnings = self.ttm.get_ttm_net_income()

        if market_cap and ttm_earnings and ttm_earnings > 0:
            return market_cap / ttm_earnings

        return None

    def calculate_roic(self, year_offset: int = 0) -> Optional[float]:
        """
        Calculate ROIC for a specific year.

        ROIC = NOPAT / Invested Capital
        NOPAT = EBIT * (1 - tax_rate)
        Invested Capital = Total Debt + Total Equity - Cash

        Args:
            year_offset: 0 for most recent, 1 for previous year, etc.
        """
        if self._annual_financials is None or self._annual_balance is None:
            return None

        if year_offset >= self._annual_financials.shape[1]:
            return None

        try:
            fin = self._annual_financials.iloc[:, year_offset]
            bal = self._annual_balance.iloc[:, year_offset]

            # Get EBIT
            ebit = fin.get("EBIT") or fin.get("Operating Income")
            if pd.isna(ebit):
                return None

            # Estimate tax rate (use 25% as typical Nordic rate)
            pretax = fin.get("Pretax Income")
            tax = fin.get("Tax Provision") or fin.get("Income Tax Expense")

            if pretax and tax and pretax > 0:
                tax_rate = abs(tax) / pretax
                tax_rate = min(max(tax_rate, 0), 0.5)  # Clamp to reasonable range
            else:
                tax_rate = 0.25  # Default Nordic corporate tax rate

            nopat = ebit * (1 - tax_rate)

            # Get invested capital components
            total_debt = (
                (bal.get("Total Debt") or 0) +
                (bal.get("Long Term Debt") or 0) if pd.isna(bal.get("Total Debt")) else bal.get("Total Debt")
            )
            if pd.isna(total_debt):
                total_debt = (bal.get("Long Term Debt") or 0) + (bal.get("Current Debt") or 0)

            total_equity = bal.get("Total Equity") or bal.get("Stockholders Equity")
            if pd.isna(total_equity):
                return None

            cash = bal.get("Cash And Cash Equivalents") or bal.get("Cash Cash Equivalents And Short Term Investments") or 0
            if pd.isna(cash):
                cash = 0

            invested_capital = float(total_debt or 0) + float(total_equity) - float(cash)

            if invested_capital <= 0:
                return None

            return float(nopat) / invested_capital

        except Exception:
            return None

    def calculate_roic_history(self, years: int = 6) -> list[float]:
        """Calculate ROIC for multiple years."""
        history = []
        for i in range(years):
            roic = self.calculate_roic(i)
            if roic is not None:
                history.append(roic)
            else:
                break
        return history

    def calculate_debt_to_equity(self) -> Optional[float]:
        """Calculate debt-to-equity ratio."""
        if self._annual_balance is None or self._annual_balance.empty:
            return None

        try:
            bal = self._annual_balance.iloc[:, 0]  # Most recent

            total_debt = bal.get("Total Debt")
            if pd.isna(total_debt):
                total_debt = (bal.get("Long Term Debt") or 0) + (bal.get("Current Debt") or 0)

            total_equity = bal.get("Total Equity") or bal.get("Stockholders Equity")

            if pd.isna(total_equity) or total_equity <= 0:
                return None

            if pd.isna(total_debt):
                total_debt = 0

            return float(total_debt) / float(total_equity)

        except Exception:
            return None

    def calculate_cf_yield(self) -> Optional[float]:
        """Calculate cash flow yield (FCF / Revenue)."""
        fcf = self.ttm.get_ttm_fcf()
        revenue = self.ttm.get_ttm_revenue()

        if fcf is None or revenue is None or revenue <= 0:
            return None

        return fcf / revenue

    def calculate_all(self) -> FinancialMetrics:
        """Calculate all metrics and return FinancialMetrics object."""
        info = self.data.get("info", {})

        ttm_earnings = self.ttm.get_ttm_net_income()
        ttm_revenue = self.ttm.get_ttm_revenue()
        ttm_fcf = self.ttm.get_ttm_fcf()
        roic_history = self.calculate_roic_history(6)

        metrics = FinancialMetrics(
            ticker=self.company.get("ticker", ""),
            name=self.company.get("name") or info.get("shortName") or info.get("longName") or "",
            exchange=self.company.get("exchange", ""),
            sector=info.get("sector"),
            industry=info.get("industry"),
            pe_ratio=self.calculate_pe_ratio(),
            market_cap=info.get("marketCap"),
            roic=roic_history[0] if roic_history else None,
            roic_history=roic_history,
            debt_to_equity=self.calculate_debt_to_equity(),
            free_cash_flow=ttm_fcf,
            cf_yield=self.calculate_cf_yield(),
            ttm_revenue=ttm_revenue,
            ttm_earnings=ttm_earnings,
            has_positive_earnings=(ttm_earnings is not None and ttm_earnings > 0),
        )

        # Check data completeness
        metrics.data_complete = all([
            metrics.pe_ratio is not None,
            metrics.roic is not None,
            metrics.debt_to_equity is not None,
            metrics.free_cash_flow is not None,
        ])

        return metrics
