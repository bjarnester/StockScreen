"""Analyzes revenue and earnings growth consistency."""

from typing import Optional
import pandas as pd


class GrowthAnalyzer:
    """Analyzes growth patterns in financial data."""

    def __init__(self, financial_data: dict):
        """
        Initialize with financial data dict.

        Args:
            financial_data: Dict from FinancialFetcher
        """
        self._annual_financials = self._parse_annual(financial_data.get("annual_financials"))

    def _parse_annual(self, data: Optional[dict]) -> Optional[pd.DataFrame]:
        """Convert annual dict to DataFrame sorted by date (oldest first for growth)."""
        if not data:
            return None

        try:
            df = pd.DataFrame(data)
            df.columns = pd.to_datetime(df.columns)
            df = df.sort_index(axis=1, ascending=True)  # Oldest first
            return df
        except Exception:
            return None

    def _get_metric_series(self, field: str) -> Optional[pd.Series]:
        """Get a time series for a specific metric."""
        if self._annual_financials is None:
            return None

        if field not in self._annual_financials.index:
            return None

        series = self._annual_financials.loc[field].dropna()
        if series.empty:
            return None

        return series

    def count_consecutive_growth_years(self, field: str) -> int:
        """
        Count consecutive years of growth (YoY increase).

        Returns number of consecutive years with positive growth,
        starting from the most recent year and going backwards.
        """
        series = self._get_metric_series(field)
        if series is None or len(series) < 2:
            return 0

        # Reverse to start from most recent
        values = series.values[::-1]
        consecutive = 0

        for i in range(len(values) - 1):
            current = values[i]
            previous = values[i + 1]

            if previous > 0 and current > previous:
                consecutive += 1
            else:
                break

        return consecutive

    def get_revenue_growth_years(self) -> int:
        """Count consecutive years of revenue growth."""
        return self.count_consecutive_growth_years("Total Revenue")

    def get_earnings_growth_years(self) -> int:
        """Count consecutive years of earnings growth."""
        return self.count_consecutive_growth_years("Net Income")

    def calculate_cagr(self, field: str, years: int = 5) -> Optional[float]:
        """
        Calculate Compound Annual Growth Rate.

        Args:
            field: Financial metric field name
            years: Number of years for CAGR calculation

        Returns:
            CAGR as decimal (0.10 = 10%)
        """
        series = self._get_metric_series(field)
        if series is None or len(series) < years + 1:
            return None

        # Get start and end values
        end_value = series.iloc[-1]
        start_value = series.iloc[-(years + 1)]

        if start_value <= 0 or end_value <= 0:
            return None

        cagr = (end_value / start_value) ** (1 / years) - 1
        return float(cagr)

    def get_revenue_cagr(self, years: int = 5) -> Optional[float]:
        """Calculate revenue CAGR."""
        return self.calculate_cagr("Total Revenue", years)

    def get_earnings_cagr(self, years: int = 5) -> Optional[float]:
        """Calculate earnings CAGR."""
        return self.calculate_cagr("Net Income", years)

    def has_consistent_growth(self, min_years: int = 5) -> dict:
        """
        Check if company has consistent revenue and earnings growth.

        Returns:
            Dict with growth analysis results
        """
        revenue_years = self.get_revenue_growth_years()
        earnings_years = self.get_earnings_growth_years()

        return {
            "revenue_growth_years": revenue_years,
            "earnings_growth_years": earnings_years,
            "revenue_consistent": revenue_years >= min_years,
            "earnings_consistent": earnings_years >= min_years,
            "both_consistent": revenue_years >= min_years and earnings_years >= min_years,
            "revenue_cagr": self.get_revenue_cagr(min_years),
            "earnings_cagr": self.get_earnings_cagr(min_years),
        }
