"""CLI entry point for Nordic Stock Screener."""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .screening.screener import Screener
from .output.pdf_generator import generate_pdf_report
from .data.cache_manager import cache
from .config import settings

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="Nordic Stock Screener")
def cli():
    """Nordic Stock Screener - Find undervalued stocks with strong fundamentals."""
    pass


@cli.command()
@click.option(
    "--exchanges", "-e",
    multiple=True,
    type=click.Choice(["oslo", "stockholm", "copenhagen"], case_sensitive=False),
    help="Exchanges to screen (default: all)"
)
@click.option(
    "--output", "-o",
    type=click.Path(dir_okay=False),
    help="Output PDF path (default: data/output/nordic_screen_YYYY-MM-DD.pdf)"
)
@click.option(
    "--top", "-n",
    default=10,
    type=int,
    help="Number of top companies to include in report (default: 10)"
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Ignore cached data and fetch fresh"
)
@click.option(
    "--min-filters", "-m",
    default=8,
    type=int,
    help="Minimum filters to pass (default: 8 = all, use 6-7 for partial matches)"
)
def scan(exchanges, output, top, no_cache, min_filters):
    """Run the stock screener and generate a PDF report."""
    console.print(Panel.fit(
        "[bold blue]Nordic Stock Screener[/bold blue]\n"
        "Screening for undervalued stocks with strong fundamentals",
        border_style="blue"
    ))

    # Clear cache if requested
    if no_cache:
        console.print("[yellow]Clearing cache...[/yellow]")
        cache.clear()

    # Determine exchanges
    exchange_list = list(exchanges) if exchanges else None

    # Run screener
    try:
        screener = Screener()
        results = screener.run(exchanges=exchange_list, min_filters=min_filters)

        if not results:
            console.print("[yellow]No companies passed all screening criteria.[/yellow]")
            console.print("Consider relaxing some criteria or checking data availability.")
            return

        # Display top results
        display_results(results[:top])

        # Generate PDF
        output_path = Path(output) if output else None
        pdf_path = generate_pdf_report(
            results=results[:top],
            total_screened=len(screener.company_fetcher.fetch_all()),
            output_path=output_path
        )

        console.print(f"\n[bold green]Report saved to:[/bold green] {pdf_path}")

    except KeyboardInterrupt:
        console.print("\n[yellow]Scan interrupted by user.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise


@cli.command()
def clear_cache():
    """Clear all cached data."""
    console.print("Clearing cache...")
    cache.clear()
    console.print("[green]Cache cleared successfully.[/green]")


@cli.command()
def info():
    """Display screener configuration and criteria."""
    table = Table(title="Screening Criteria", show_header=True, header_style="bold blue")
    table.add_column("Criterion", style="cyan")
    table.add_column("Threshold", style="green")

    thresholds = settings.thresholds
    table.add_row("PE Ratio", "Below industry average")
    table.add_row("ROIC", f"> {thresholds.min_roic*100:.0f}% for {thresholds.roic_years} years")
    table.add_row("Revenue Growth", f"Consistent for {thresholds.growth_years} years")
    table.add_row("Earnings Growth", f"Consistent for {thresholds.growth_years} years")
    table.add_row("Debt-to-Equity", f"< {thresholds.max_debt_to_equity}")
    table.add_row("Free Cash Flow", "Positive")
    table.add_row("CF Yield", f">= {thresholds.min_cf_yield*100:.0f}%")
    table.add_row("Earnings", "Positive (exclude loss-makers)")

    console.print(table)

    console.print("\n[bold]Exchanges:[/bold]")
    for key, exchange in settings.exchanges.items():
        console.print(f"  • {exchange.name} ({exchange.suffix})")


def display_results(results):
    """Display screening results in a table."""
    if not results:
        return

    table = Table(
        title=f"Top {len(results)} Undervalued Companies",
        show_header=True,
        header_style="bold blue"
    )

    table.add_column("#", style="dim", width=3)
    table.add_column("Company", style="cyan", max_width=30)
    table.add_column("Ticker", style="green")
    table.add_column("Exchange")
    table.add_column("PE", justify="right")
    table.add_column("ROIC", justify="right")
    table.add_column("D/E", justify="right")
    table.add_column("CF%", justify="right")
    table.add_column("Score", justify="right", style="bold")

    for idx, result in enumerate(results, 1):
        m = result.metrics
        table.add_row(
            str(idx),
            (m.name or "")[:30],
            m.ticker,
            m.exchange.title(),
            f"{m.pe_ratio:.1f}" if m.pe_ratio else "N/A",
            f"{m.roic*100:.1f}%" if m.roic else "N/A",
            f"{m.debt_to_equity:.2f}" if m.debt_to_equity else "N/A",
            f"{m.cf_yield*100:.1f}%" if m.cf_yield else "N/A",
            f"{result.score:.1f}",
        )

    console.print(table)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
