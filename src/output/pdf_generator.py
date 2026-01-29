"""PDF report generation using fpdf2."""

from datetime import datetime
from pathlib import Path
from typing import Optional
from fpdf import FPDF

from ..screening.filters import ScreeningResult
from ..config import settings


class PDFReport(FPDF):
    """Custom PDF class for stock screening reports."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        """Page header."""
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(26, 95, 122)
        self.cell(0, 10, "Nordic Stock Screener Report", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        """Page footer."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


class PDFGenerator:
    """Generates PDF reports from screening results."""

    def __init__(self, results: list[ScreeningResult], total_screened: int):
        """
        Initialize PDF generator.

        Args:
            results: List of ScreeningResult (companies that passed)
            total_screened: Total number of companies screened
        """
        self.results = results
        self.total_screened = total_screened
        self.pdf = PDFReport()
        self.pdf.alias_nb_pages()

    def generate(self, output_path: Optional[Path] = None) -> Path:
        """
        Generate the PDF report.

        Args:
            output_path: Optional output path. If None, uses default.

        Returns:
            Path to generated PDF file.
        """
        if output_path is None:
            settings.ensure_dirs()
            date_str = datetime.now().strftime("%Y-%m-%d")
            output_path = settings.output_dir / f"nordic_screen_{date_str}.pdf"

        self.pdf.add_page()
        self._add_summary()
        self._add_criteria()
        self._add_top_companies_table()
        self._add_detailed_analysis()
        self._add_disclaimer()

        self.pdf.output(str(output_path))
        return output_path

    def _add_summary(self):
        """Add summary section."""
        self.pdf.set_font("Helvetica", "B", 16)
        self.pdf.set_text_color(26, 95, 122)
        self.pdf.cell(0, 10, "Summary", new_x="LMARGIN", new_y="NEXT")

        self.pdf.set_font("Helvetica", "", 10)
        self.pdf.set_text_color(0, 0, 0)

        report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.pdf.cell(0, 6, f"Generated: {report_date}", new_x="LMARGIN", new_y="NEXT")
        self.pdf.cell(0, 6, f"Companies Screened: {self.total_screened}", new_x="LMARGIN", new_y="NEXT")
        self.pdf.cell(0, 6, f"Passed All Criteria: {len(self.results)}", new_x="LMARGIN", new_y="NEXT")
        self.pdf.cell(0, 6, "Exchanges: Oslo, Stockholm, Copenhagen", new_x="LMARGIN", new_y="NEXT")
        self.pdf.ln(5)

    def _add_criteria(self):
        """Add screening criteria section."""
        self.pdf.set_font("Helvetica", "B", 12)
        self.pdf.set_text_color(26, 95, 122)
        self.pdf.cell(0, 10, "Screening Criteria", new_x="LMARGIN", new_y="NEXT")

        self.pdf.set_font("Helvetica", "", 9)
        self.pdf.set_text_color(0, 0, 0)

        t = settings.thresholds
        criteria = [
            f"PE Ratio <= {t.max_pe:.0f}",
            f"ROIC > {t.min_roic*100:.0f}% for last {t.roic_years} years",
            f"Consistent revenue growth for {t.revenue_growth_years} years",
            f"Consistent earnings growth for {t.earnings_growth_years} years",
            f"Debt-to-Equity < {t.max_debt_to_equity}",
            "Positive Free Cash Flow",
            f"Cash Flow Yield >= {t.min_cf_yield*100:.0f}%",
            "Positive Earnings (exclude loss-makers)",
        ]

        for c in criteria:
            self.pdf.cell(0, 5, f"  - {c}", new_x="LMARGIN", new_y="NEXT")

        self.pdf.ln(5)

    def _add_top_companies_table(self):
        """Add top companies summary table."""
        self.pdf.set_font("Helvetica", "B", 12)
        self.pdf.set_text_color(26, 95, 122)
        self.pdf.cell(0, 10, f"Top {len(self.results)} Undervalued Companies", new_x="LMARGIN", new_y="NEXT")

        if not self.results:
            self.pdf.set_font("Helvetica", "I", 10)
            self.pdf.set_text_color(128, 128, 128)
            self.pdf.cell(0, 10, "No companies passed all screening criteria.", new_x="LMARGIN", new_y="NEXT")
            return

        # Table header
        self.pdf.set_font("Helvetica", "B", 8)
        self.pdf.set_fill_color(26, 95, 122)
        self.pdf.set_text_color(255, 255, 255)

        col_widths = [8, 45, 25, 25, 20, 15, 15, 15, 15, 12]
        headers = ["#", "Company", "Ticker", "Exchange", "Sector", "PE", "ROIC", "D/E", "CF%", "Score"]

        for i, header in enumerate(headers):
            self.pdf.cell(col_widths[i], 7, header, border=1, fill=True, align="C")
        self.pdf.ln()

        # Table rows
        self.pdf.set_font("Helvetica", "", 7)
        self.pdf.set_text_color(0, 0, 0)

        for idx, result in enumerate(self.results, 1):
            m = result.metrics

            row_data = [
                str(idx),
                (m.name or "")[:25],
                m.ticker[:15],
                (m.exchange or "").title()[:12],
                (m.sector or "N/A")[:12],
                f"{m.pe_ratio:.1f}" if m.pe_ratio else "N/A",
                f"{m.roic*100:.1f}%" if m.roic else "N/A",
                f"{m.debt_to_equity:.2f}" if m.debt_to_equity else "N/A",
                f"{m.cf_yield*100:.1f}%" if m.cf_yield else "N/A",
                f"{result.score:.1f}",
            ]

            fill = idx % 2 == 0
            if fill:
                self.pdf.set_fill_color(245, 249, 250)

            for i, data in enumerate(row_data):
                self.pdf.cell(col_widths[i], 6, data, border=1, fill=fill, align="C" if i in [0, 5, 6, 7, 8, 9] else "L")
            self.pdf.ln()

        self.pdf.ln(5)

    def _add_detailed_analysis(self):
        """Add detailed analysis for each company."""
        if not self.results:
            return

        self.pdf.add_page()
        self.pdf.set_font("Helvetica", "B", 14)
        self.pdf.set_text_color(26, 95, 122)
        self.pdf.cell(0, 10, "Detailed Analysis", new_x="LMARGIN", new_y="NEXT")

        for idx, result in enumerate(self.results, 1):
            if self.pdf.get_y() > 220:
                self.pdf.add_page()

            self._add_company_detail(idx, result)

    def _add_company_detail(self, rank: int, result: ScreeningResult):
        """Add detailed section for one company."""
        m = result.metrics

        # Company header
        self.pdf.set_font("Helvetica", "B", 11)
        self.pdf.set_text_color(26, 95, 122)
        self.pdf.cell(0, 8, f"{rank}. {m.name} ({m.ticker})", new_x="LMARGIN", new_y="NEXT")

        # Key metrics
        self.pdf.set_font("Helvetica", "", 9)
        self.pdf.set_text_color(0, 0, 0)

        metrics_line = f"Exchange: {m.exchange.title()} | Sector: {m.sector or 'N/A'} | Industry: {m.industry or 'N/A'}"
        self.pdf.cell(0, 5, metrics_line, new_x="LMARGIN", new_y="NEXT")

        pe_str = f"{m.pe_ratio:.1f}" if m.pe_ratio else "N/A"
        roic_str = f"{m.roic*100:.1f}%" if m.roic else "N/A"
        de_str = f"{m.debt_to_equity:.2f}" if m.debt_to_equity else "N/A"
        cf_str = f"{m.cf_yield*100:.1f}%" if m.cf_yield else "N/A"
        metrics_line2 = f"PE: {pe_str} | ROIC: {roic_str} | D/E: {de_str} | CF Yield: {cf_str}"
        self.pdf.cell(0, 5, metrics_line2, new_x="LMARGIN", new_y="NEXT")

        growth_line = (
            f"Revenue Growth: {m.revenue_growth_years or 0} years | "
            f"Earnings Growth: {m.earnings_growth_years or 0} years | "
            f"Score: {result.score:.1f}"
        )
        self.pdf.cell(0, 5, growth_line, new_x="LMARGIN", new_y="NEXT")

        # Filter results
        self.pdf.set_font("Helvetica", "", 8)
        for name, fr in result.filter_results.items():
            status = "PASS" if fr.passed else "FAIL"
            color = (46, 125, 50) if fr.passed else (198, 40, 40)
            self.pdf.set_text_color(*color)
            self.pdf.cell(15, 4, f"[{status}]", new_x="RIGHT")
            self.pdf.set_text_color(0, 0, 0)
            self.pdf.cell(0, 4, f" {name.replace('_', ' ').title()}: {fr.reason}", new_x="LMARGIN", new_y="NEXT")

        self.pdf.ln(5)

    def _add_disclaimer(self):
        """Add disclaimer at the end."""
        self.pdf.ln(10)
        self.pdf.set_font("Helvetica", "I", 8)
        self.pdf.set_text_color(128, 128, 128)
        self.pdf.multi_cell(
            0, 4,
            "Disclaimer: This report is for informational purposes only and should not be considered "
            "investment advice. Data sourced from Yahoo Finance. Past performance does not guarantee "
            "future results. Always conduct your own research before making investment decisions."
        )


def generate_pdf_report(
    results: list[ScreeningResult],
    total_screened: int,
    output_path: Optional[Path] = None
) -> Path:
    """
    Convenience function to generate PDF report.

    Args:
        results: List of ScreeningResult (companies that passed)
        total_screened: Total number of companies screened
        output_path: Optional output path

    Returns:
        Path to generated PDF file
    """
    generator = PDFGenerator(results, total_screened)
    return generator.generate(output_path)
