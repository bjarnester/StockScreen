"""Main stock screener orchestrator."""

from typing import Optional, Callable
from rich.console import Console
from rich.progress import Progress, TaskID

from ..data.company_fetcher import CompanyFetcher
from ..data.financial_fetcher import FinancialFetcher
from ..calculations.metrics import MetricsCalculator, FinancialMetrics
from ..calculations.growth_analyzer import GrowthAnalyzer
from ..calculations.industry_averages import IndustryAverages
from .filters import StockFilters, ScreeningResult, FilterResult

console = Console()


class Screener:
    """Orchestrates the stock screening process."""

    def __init__(self):
        self.company_fetcher = CompanyFetcher()
        self.financial_fetcher = FinancialFetcher()
        self.industry_averages = IndustryAverages()
        self.filters: Optional[StockFilters] = None

    def run(
        self,
        exchanges: Optional[list[str]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        min_filters: int = 8
    ) -> list[ScreeningResult]:
        """
        Run the complete screening process.

        Args:
            exchanges: List of exchanges to screen (None = all)
            progress_callback: Optional callback(stage, current, total)
            min_filters: Minimum number of filters to pass (default 8 = all)

        Returns:
            List of ScreeningResult for companies passing minimum filters
        """
        # Step 1: Fetch company lists
        console.print("[bold blue]Step 1: Fetching company lists...[/bold blue]")
        all_companies = self._fetch_companies(exchanges)
        console.print(f"Found {len(all_companies)} companies")

        # Step 2: Fetch financial data and calculate metrics
        console.print("[bold blue]Step 2: Fetching financial data...[/bold blue]")
        all_metrics = self._fetch_and_calculate_metrics(all_companies, progress_callback)
        console.print(f"Retrieved data for {len(all_metrics)} companies")

        # Step 3: Build industry averages
        console.print("[bold blue]Step 3: Calculating industry averages...[/bold blue]")
        self._build_industry_averages(all_metrics)

        # Step 4: Initialize filters
        self.filters = StockFilters(self.industry_averages)

        # Step 5: Apply screening filters
        console.print("[bold blue]Step 4: Applying screening criteria...[/bold blue]")
        results = self._screen_companies(all_metrics, progress_callback)

        # Step 6: Sort and return
        passed = [r for r in results if r.passed_count >= min_filters]
        passed.sort(key=lambda r: r.score, reverse=True)

        if min_filters == 8:
            console.print(f"[bold green]Found {len(passed)} companies passing all criteria[/bold green]")
        else:
            console.print(f"[bold green]Found {len(passed)} companies passing {min_filters}+ filters[/bold green]")
        return passed

    def _fetch_companies(self, exchanges: Optional[list[str]]) -> list[dict]:
        """Fetch company lists from specified exchanges."""
        all_companies = []

        if exchanges is None:
            exchanges = ["oslo", "stockholm", "copenhagen"]

        for exchange in exchanges:
            if exchange == "oslo":
                companies = self.company_fetcher.fetch_oslo()
            elif exchange in ["stockholm", "copenhagen"]:
                companies = self.company_fetcher.fetch_nasdaq_nordic(exchange)
            else:
                continue

            all_companies.extend(companies)

        return all_companies

    def _fetch_and_calculate_metrics(
        self,
        companies: list[dict],
        progress_callback: Optional[Callable]
    ) -> list[tuple[dict, dict, FinancialMetrics, dict]]:
        """
        Fetch financial data and calculate metrics for all companies.

        Returns list of (company_info, financial_data, metrics, growth_data)
        """
        results = []
        total = len(companies)

        with Progress() as progress:
            task = progress.add_task("[cyan]Fetching financials...", total=total)

            for i, company in enumerate(companies):
                ticker = company["ticker"]
                progress.update(task, advance=1, description=f"[cyan]Fetching {ticker}...")

                if progress_callback:
                    progress_callback("fetching", i + 1, total)

                financial_data = self.financial_fetcher.fetch_financials(ticker)
                if not financial_data:
                    continue

                try:
                    # Calculate metrics
                    calc = MetricsCalculator(financial_data, company)
                    metrics = calc.calculate_all()

                    # Analyze growth
                    growth = GrowthAnalyzer(financial_data)
                    growth_data = growth.has_consistent_growth()

                    results.append((company, financial_data, metrics, growth_data))

                except Exception as e:
                    console.print(f"[yellow]Error processing {ticker}: {e}[/yellow]")
                    continue

        return results

    def _build_industry_averages(
        self,
        data: list[tuple[dict, dict, FinancialMetrics, dict]]
    ) -> None:
        """Build industry average PE ratios from collected data."""
        for _, _, metrics, _ in data:
            self.industry_averages.add_company(
                metrics.industry,
                metrics.sector,
                metrics.pe_ratio
            )

    def _screen_companies(
        self,
        data: list[tuple[dict, dict, FinancialMetrics, dict]],
        progress_callback: Optional[Callable]
    ) -> list[ScreeningResult]:
        """Apply all screening filters to companies."""
        results = []
        total = len(data)

        with Progress() as progress:
            task = progress.add_task("[cyan]Screening...", total=total)

            for i, (company, financial_data, metrics, growth_data) in enumerate(data):
                progress.update(task, advance=1, description=f"[cyan]Screening {metrics.ticker}...")

                if progress_callback:
                    progress_callback("screening", i + 1, total)

                result = self._apply_filters(metrics, growth_data)
                results.append(result)

        return results

    def _apply_filters(self, metrics: FinancialMetrics, growth_data: dict) -> ScreeningResult:
        """Apply all filters to a company and return result."""
        filter_results = {}

        # Apply each filter
        filter_results["pe_below_max"] = self.filters.filter_pe_below_max(metrics)
        filter_results["roic_consistent"] = self.filters.filter_roic_consistent(metrics)
        filter_results["revenue_growth"] = self.filters.filter_revenue_growth(
            metrics, growth_data.get("revenue_growth_years")
        )
        filter_results["earnings_growth"] = self.filters.filter_earnings_growth(
            metrics, growth_data.get("earnings_growth_years")
        )
        filter_results["debt_to_equity"] = self.filters.filter_debt_to_equity(metrics)
        filter_results["positive_fcf"] = self.filters.filter_positive_fcf(metrics)
        filter_results["cf_yield"] = self.filters.filter_cf_yield(metrics)
        filter_results["positive_earnings"] = self.filters.filter_positive_earnings(metrics)

        # Check if all passed
        passed_all = all(r.passed for r in filter_results.values())

        # Calculate composite score for ranking
        score = self._calculate_score(metrics, growth_data, filter_results)

        # Update metrics with growth data
        metrics.revenue_growth_years = growth_data.get("revenue_growth_years")
        metrics.earnings_growth_years = growth_data.get("earnings_growth_years")

        return ScreeningResult(
            metrics=metrics,
            passed_all=passed_all,
            filter_results=filter_results,
            score=score
        )

    def _calculate_score(
        self,
        metrics: FinancialMetrics,
        growth_data: dict,
        filter_results: dict[str, FilterResult]
    ) -> float:
        """
        Calculate composite score for ranking.

        Higher score = more attractive investment.
        """
        score = 0.0

        # ROIC contribution (0-30 points)
        if metrics.roic is not None:
            roic_score = min(metrics.roic * 100, 30)  # Cap at 30%
            score += roic_score

        # PE discount contribution (0-20 points)
        pe_result = filter_results.get("pe_below_max")
        if pe_result and pe_result.value and pe_result.threshold:
            discount = (pe_result.threshold - pe_result.value) / pe_result.threshold
            pe_score = max(0, min(discount * 40, 20))  # Up to 20 points for 50% discount
            score += pe_score

        # CF yield contribution (0-20 points)
        if metrics.cf_yield is not None:
            cf_score = min(metrics.cf_yield * 100, 20)
            score += cf_score

        # Low debt contribution (0-15 points)
        if metrics.debt_to_equity is not None:
            de_score = max(0, 15 - metrics.debt_to_equity * 30)
            score += de_score

        # Growth consistency (0-15 points)
        rev_years = growth_data.get("revenue_growth_years", 0)
        earn_years = growth_data.get("earnings_growth_years", 0)
        growth_score = min((rev_years + earn_years) * 1.5, 15)
        score += growth_score

        return score

    def get_top_n(self, results: list[ScreeningResult], n: int = 10) -> list[ScreeningResult]:
        """Get top N results by score."""
        sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
        return sorted_results[:n]
