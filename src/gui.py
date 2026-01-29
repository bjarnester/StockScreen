"""GUI for Nordic Stock Screener."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import subprocess
import sys
from pathlib import Path

from .config import settings
from .screening.screener import Screener
from .output.pdf_generator import generate_pdf_report


class StockScreenerGUI:
    """Main GUI application for the Nordic Stock Screener."""

    def __init__(self, root):
        self.root = root
        self.root.title("Nordic Stock Screener")
        self.root.geometry("600x700")
        self.root.resizable(True, True)

        # Variables for thresholds
        self.max_pe = tk.DoubleVar(value=settings.thresholds.max_pe)
        self.min_roic = tk.DoubleVar(value=settings.thresholds.min_roic * 100)
        self.roic_years = tk.IntVar(value=settings.thresholds.roic_years)
        self.growth_years = tk.IntVar(value=settings.thresholds.growth_years)
        self.max_de = tk.DoubleVar(value=settings.thresholds.max_debt_to_equity)
        self.min_cf_yield = tk.DoubleVar(value=settings.thresholds.min_cf_yield * 100)
        self.min_filters = tk.IntVar(value=8)

        # Exchange selection
        self.oslo_var = tk.BooleanVar(value=True)
        self.stockholm_var = tk.BooleanVar(value=True)
        self.copenhagen_var = tk.BooleanVar(value=True)

        # Results
        self.results = []
        self.total_screened = 0
        self.last_pdf_path = None

        self._create_widgets()

    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="Nordic Stock Screener",
            font=("Helvetica", 16, "bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 15))

        # Exchanges frame
        exchanges_frame = ttk.LabelFrame(main_frame, text="Exchanges", padding="10")
        exchanges_frame.grid(row=1, column=0, sticky="ew", pady=5)
        exchanges_frame.columnconfigure((0, 1, 2), weight=1)

        ttk.Checkbutton(exchanges_frame, text="Oslo Bors", variable=self.oslo_var).grid(row=0, column=0)
        ttk.Checkbutton(exchanges_frame, text="Nasdaq Stockholm", variable=self.stockholm_var).grid(row=0, column=1)
        ttk.Checkbutton(exchanges_frame, text="Nasdaq Copenhagen", variable=self.copenhagen_var).grid(row=0, column=2)

        # Thresholds frame
        thresholds_frame = ttk.LabelFrame(main_frame, text="Screening Thresholds", padding="10")
        thresholds_frame.grid(row=2, column=0, sticky="ew", pady=10)
        thresholds_frame.columnconfigure(1, weight=1)

        # Max PE
        ttk.Label(thresholds_frame, text="Max PE:").grid(row=0, column=0, sticky="w", pady=5)
        pe_spin = ttk.Spinbox(thresholds_frame, from_=1, to=100, increment=1, textvariable=self.max_pe, width=10)
        pe_spin.grid(row=0, column=1, sticky="w", pady=5, padx=5)
        ttk.Label(thresholds_frame, text="Maximum price-to-earnings ratio").grid(row=0, column=2, sticky="w")

        # Min ROIC
        ttk.Label(thresholds_frame, text="Min ROIC (%):").grid(row=1, column=0, sticky="w", pady=5)
        roic_spin = ttk.Spinbox(thresholds_frame, from_=0, to=50, increment=1, textvariable=self.min_roic, width=10)
        roic_spin.grid(row=1, column=1, sticky="w", pady=5, padx=5)
        ttk.Label(thresholds_frame, text="Minimum return on invested capital").grid(row=1, column=2, sticky="w")

        # ROIC Years
        ttk.Label(thresholds_frame, text="ROIC Years:").grid(row=2, column=0, sticky="w", pady=5)
        roic_years_spin = ttk.Spinbox(thresholds_frame, from_=1, to=10, increment=1, textvariable=self.roic_years, width=10)
        roic_years_spin.grid(row=2, column=1, sticky="w", pady=5, padx=5)
        ttk.Label(thresholds_frame, text="Years of ROIC history required").grid(row=2, column=2, sticky="w")

        # Growth Years
        ttk.Label(thresholds_frame, text="Growth Years:").grid(row=3, column=0, sticky="w", pady=5)
        growth_spin = ttk.Spinbox(thresholds_frame, from_=1, to=10, increment=1, textvariable=self.growth_years, width=10)
        growth_spin.grid(row=3, column=1, sticky="w", pady=5, padx=5)
        ttk.Label(thresholds_frame, text="Consecutive growth years required").grid(row=3, column=2, sticky="w")

        # Max D/E
        ttk.Label(thresholds_frame, text="Max Debt/Equity:").grid(row=4, column=0, sticky="w", pady=5)
        de_spin = ttk.Spinbox(thresholds_frame, from_=0.1, to=5.0, increment=0.1, textvariable=self.max_de, width=10)
        de_spin.grid(row=4, column=1, sticky="w", pady=5, padx=5)
        ttk.Label(thresholds_frame, text="Maximum debt-to-equity ratio").grid(row=4, column=2, sticky="w")

        # Min CF Yield
        ttk.Label(thresholds_frame, text="Min CF Yield (%):").grid(row=5, column=0, sticky="w", pady=5)
        cf_spin = ttk.Spinbox(thresholds_frame, from_=0, to=30, increment=1, textvariable=self.min_cf_yield, width=10)
        cf_spin.grid(row=5, column=1, sticky="w", pady=5, padx=5)
        ttk.Label(thresholds_frame, text="Minimum free cash flow yield").grid(row=5, column=2, sticky="w")

        # Min Filters
        ttk.Label(thresholds_frame, text="Min Filters:").grid(row=6, column=0, sticky="w", pady=5)
        filters_spin = ttk.Spinbox(thresholds_frame, from_=1, to=8, increment=1, textvariable=self.min_filters, width=10)
        filters_spin.grid(row=6, column=1, sticky="w", pady=5, padx=5)
        ttk.Label(thresholds_frame, text="Minimum filters to pass (8 = all)").grid(row=6, column=2, sticky="w")

        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=0, pady=15)

        self.scan_button = ttk.Button(buttons_frame, text="Run Screener", command=self._run_screener)
        self.scan_button.grid(row=0, column=0, padx=5)

        self.open_pdf_button = ttk.Button(buttons_frame, text="Open Report", command=self._open_pdf, state="disabled")
        self.open_pdf_button.grid(row=0, column=1, padx=5)

        ttk.Button(buttons_frame, text="Reset Defaults", command=self._reset_defaults).grid(row=0, column=2, padx=5)

        # Progress frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=4, column=0, sticky="ew", pady=5)
        progress_frame.columnconfigure(0, weight=1)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky="ew")

        self.status_label = ttk.Label(progress_frame, text="Ready")
        self.status_label.grid(row=1, column=0, sticky="w", pady=5)

        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="10")
        results_frame.grid(row=5, column=0, sticky="nsew", pady=10)
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)

        # Treeview for results
        columns = ("rank", "company", "ticker", "exchange", "pe", "roic", "de", "cf", "filters", "score")
        self.tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=15)

        self.tree.heading("rank", text="#")
        self.tree.heading("company", text="Company")
        self.tree.heading("ticker", text="Ticker")
        self.tree.heading("exchange", text="Exchange")
        self.tree.heading("pe", text="PE")
        self.tree.heading("roic", text="ROIC")
        self.tree.heading("de", text="D/E")
        self.tree.heading("cf", text="CF%")
        self.tree.heading("filters", text="Filters")
        self.tree.heading("score", text="Score")

        self.tree.column("rank", width=40, anchor="center")
        self.tree.column("company", width=150)
        self.tree.column("ticker", width=80)
        self.tree.column("exchange", width=80)
        self.tree.column("pe", width=50, anchor="e")
        self.tree.column("roic", width=60, anchor="e")
        self.tree.column("de", width=50, anchor="e")
        self.tree.column("cf", width=50, anchor="e")
        self.tree.column("filters", width=50, anchor="center")
        self.tree.column("score", width=50, anchor="e")

        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Summary label
        self.summary_label = ttk.Label(results_frame, text="")
        self.summary_label.grid(row=1, column=0, sticky="w", pady=5)

    def _update_settings(self):
        """Update settings with current GUI values."""
        settings.thresholds.max_pe = self.max_pe.get()
        settings.thresholds.min_roic = self.min_roic.get() / 100
        settings.thresholds.roic_years = self.roic_years.get()
        settings.thresholds.growth_years = self.growth_years.get()
        settings.thresholds.max_debt_to_equity = self.max_de.get()
        settings.thresholds.min_cf_yield = self.min_cf_yield.get() / 100

    def _get_selected_exchanges(self):
        """Get list of selected exchanges."""
        exchanges = []
        if self.oslo_var.get():
            exchanges.append("oslo")
        if self.stockholm_var.get():
            exchanges.append("stockholm")
        if self.copenhagen_var.get():
            exchanges.append("copenhagen")
        return exchanges if exchanges else None

    def _run_screener(self):
        """Run the screener in a background thread."""
        exchanges = self._get_selected_exchanges()
        if not exchanges:
            messagebox.showwarning("Warning", "Please select at least one exchange.")
            return

        self._update_settings()
        self.scan_button.config(state="disabled")
        self.open_pdf_button.config(state="disabled")
        self.progress_var.set(0)
        self.status_label.config(text="Starting...")

        # Clear previous results
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Run in background thread
        thread = threading.Thread(target=self._run_screener_thread, args=(exchanges,))
        thread.daemon = True
        thread.start()

    def _run_screener_thread(self, exchanges):
        """Background thread for running the screener."""
        try:
            self.root.after(0, lambda: self.status_label.config(text="Fetching company lists..."))
            self.root.after(0, lambda: self.progress_var.set(10))

            screener = Screener()

            self.root.after(0, lambda: self.status_label.config(text="Fetching financial data..."))
            self.root.after(0, lambda: self.progress_var.set(30))

            results = screener.run(
                exchanges=exchanges,
                min_filters=self.min_filters.get()
            )

            self.root.after(0, lambda: self.progress_var.set(80))
            self.root.after(0, lambda: self.status_label.config(text="Generating PDF report..."))

            # Generate PDF
            self.total_screened = len(screener.company_fetcher.fetch_all())
            settings.ensure_dirs()
            from datetime import datetime
            date_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            pdf_path = settings.output_dir / f"nordic_screen_{date_str}.pdf"

            generate_pdf_report(results, self.total_screened, pdf_path)
            self.last_pdf_path = pdf_path

            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self._display_results(results))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.status_label.config(text=f"Error: {e}"))

        finally:
            self.root.after(0, lambda: self.scan_button.config(state="normal"))

    def _display_results(self, results):
        """Display results in the treeview."""
        self.results = results

        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, r in enumerate(results, 1):
            m = r.metrics
            pe = f"{m.pe_ratio:.1f}" if m.pe_ratio else "N/A"
            roic = f"{m.roic*100:.1f}%" if m.roic else "N/A"
            de = f"{m.debt_to_equity:.2f}" if m.debt_to_equity else "N/A"
            cf = f"{m.cf_yield*100:.1f}%" if m.cf_yield else "N/A"

            self.tree.insert("", "end", values=(
                i,
                (m.name or "")[:25],
                m.ticker,
                m.exchange.title(),
                pe,
                roic,
                de,
                cf,
                r.passed_count,
                f"{r.score:.1f}"
            ))

        self.summary_label.config(
            text=f"Found {len(results)} companies passing {self.min_filters.get()}+ filters (from {self.total_screened} screened)"
        )
        self.status_label.config(text=f"Complete! Report saved to: {self.last_pdf_path}")
        self.open_pdf_button.config(state="normal")

    def _open_pdf(self):
        """Open the generated PDF report."""
        if self.last_pdf_path and self.last_pdf_path.exists():
            if sys.platform == "win32":
                os.startfile(str(self.last_pdf_path))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(self.last_pdf_path)])
            else:
                subprocess.run(["xdg-open", str(self.last_pdf_path)])
        else:
            messagebox.showwarning("Warning", "No report available. Run the screener first.")

    def _reset_defaults(self):
        """Reset all values to defaults."""
        self.max_pe.set(15.0)
        self.min_roic.set(10.0)
        self.roic_years.set(3)
        self.growth_years.set(3)
        self.max_de.set(1.0)
        self.min_cf_yield.set(5.0)
        self.min_filters.set(8)
        self.oslo_var.set(True)
        self.stockholm_var.set(True)
        self.copenhagen_var.set(True)


def main():
    """Launch the GUI application."""
    root = tk.Tk()
    app = StockScreenerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
