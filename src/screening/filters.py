"""Individual screening filters for stock selection."""

from typing import Optional
from dataclasses import dataclass

from ..calculations.metrics import FinancialMetrics
from ..calculations.industry_averages import IndustryAverages
from ..config import settings


@dataclass
class FilterResult:
    """Result of applying a filter."""
    passed: bool
    reason: str
    value: Optional[float] = None
    threshold: Optional[float] = None


class StockFilters:
    """Collection of screening filters."""

    def __init__(self, industry_averages: IndustryAverages):
        """
        Initialize filters.

        Args:
            industry_averages: IndustryAverages instance for PE comparison
        """
        self.industry_avg = industry_averages
        self.thresholds = settings.thresholds

    def filter_pe_below_industry(self, metrics: FinancialMetrics) -> FilterResult:
        """Check if PE is below industry average."""
        if metrics.pe_ratio is None:
            return FilterResult(False, "PE ratio not available")

        peer_avg = self.industry_avg.get_peer_average(metrics.industry, metrics.sector)

        if peer_avg is None:
            # If no peer data, use market average of ~20
            peer_avg = 20.0

        passed = metrics.pe_ratio < peer_avg

        return FilterResult(
            passed=passed,
            reason=f"PE {metrics.pe_ratio:.1f} {'<' if passed else '>='} industry avg {peer_avg:.1f}",
            value=metrics.pe_ratio,
            threshold=peer_avg
        )

    def filter_roic_consistent(self, metrics: FinancialMetrics) -> FilterResult:
        """Check if ROIC > 10% for required years."""
        min_roic = self.thresholds.min_roic
        required_years = self.thresholds.roic_years

        if not metrics.roic_history:
            return FilterResult(False, "ROIC history not available")

        years_above = sum(1 for r in metrics.roic_history if r >= min_roic)

        passed = years_above >= required_years

        return FilterResult(
            passed=passed,
            reason=f"ROIC>{min_roic*100:.0f}% for {years_above}/{required_years} years",
            value=metrics.roic,
            threshold=min_roic
        )

    def filter_revenue_growth(self, metrics: FinancialMetrics, growth_years: int) -> FilterResult:
        """Check for consistent revenue growth."""
        required_years = self.thresholds.growth_years

        if growth_years is None:
            return FilterResult(False, "Revenue growth data not available")

        passed = growth_years >= required_years

        return FilterResult(
            passed=passed,
            reason=f"Revenue growth: {growth_years}/{required_years} consecutive years",
            value=float(growth_years),
            threshold=float(required_years)
        )

    def filter_earnings_growth(self, metrics: FinancialMetrics, growth_years: int) -> FilterResult:
        """Check for consistent earnings growth."""
        required_years = self.thresholds.growth_years

        if growth_years is None:
            return FilterResult(False, "Earnings growth data not available")

        passed = growth_years >= required_years

        return FilterResult(
            passed=passed,
            reason=f"Earnings growth: {growth_years}/{required_years} consecutive years",
            value=float(growth_years),
            threshold=float(required_years)
        )

    def filter_debt_to_equity(self, metrics: FinancialMetrics) -> FilterResult:
        """Check if D/E ratio is below threshold."""
        max_de = self.thresholds.max_debt_to_equity

        if metrics.debt_to_equity is None:
            return FilterResult(False, "D/E ratio not available")

        passed = metrics.debt_to_equity < max_de

        return FilterResult(
            passed=passed,
            reason=f"D/E {metrics.debt_to_equity:.2f} {'<' if passed else '>='} {max_de}",
            value=metrics.debt_to_equity,
            threshold=max_de
        )

    def filter_positive_fcf(self, metrics: FinancialMetrics) -> FilterResult:
        """Check if free cash flow is positive."""
        if metrics.free_cash_flow is None:
            return FilterResult(False, "FCF not available")

        passed = metrics.free_cash_flow > 0

        fcf_m = metrics.free_cash_flow / 1_000_000

        return FilterResult(
            passed=passed,
            reason=f"FCF: {fcf_m:.1f}M {'(positive)' if passed else '(negative)'}",
            value=metrics.free_cash_flow,
            threshold=0
        )

    def filter_cf_yield(self, metrics: FinancialMetrics) -> FilterResult:
        """Check if cash flow yield meets threshold."""
        min_yield = self.thresholds.min_cf_yield

        if metrics.cf_yield is None:
            return FilterResult(False, "CF yield not available")

        passed = metrics.cf_yield >= min_yield

        return FilterResult(
            passed=passed,
            reason=f"CF yield {metrics.cf_yield*100:.1f}% {'>=' if passed else '<'} {min_yield*100:.0f}%",
            value=metrics.cf_yield,
            threshold=min_yield
        )

    def filter_positive_earnings(self, metrics: FinancialMetrics) -> FilterResult:
        """Check if company has positive earnings."""
        passed = metrics.has_positive_earnings

        earnings_m = (metrics.ttm_earnings or 0) / 1_000_000

        return FilterResult(
            passed=passed,
            reason=f"TTM Earnings: {earnings_m:.1f}M {'(profitable)' if passed else '(loss-maker)'}",
            value=metrics.ttm_earnings,
            threshold=0
        )


@dataclass
class ScreeningResult:
    """Complete screening result for a company."""
    metrics: FinancialMetrics
    passed_all: bool
    filter_results: dict[str, FilterResult]
    score: float  # Composite score for ranking

    @property
    def passed_count(self) -> int:
        """Count of passed filters."""
        return sum(1 for r in self.filter_results.values() if r.passed)

    @property
    def total_filters(self) -> int:
        """Total number of filters applied."""
        return len(self.filter_results)
