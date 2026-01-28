# Nordic Stock Screener

A Python application to screen undervalued stocks from Oslo Bors, Nasdaq Stockholm, and Nasdaq Copenhagen with strong fundamentals.

## Screening Criteria

| Filter | Threshold |
|--------|-----------|
| PE Ratio | Below industry average |
| ROIC | > 10% for last 6 years |
| Revenue Growth | Consistent for 5 years |
| Earnings Growth | Consistent for 5 years |
| Debt-to-Equity | < 0.5 |
| Free Cash Flow | Positive |
| CF Yield (FCF/Revenue) | >= 5% |
| Earnings | Positive (exclude loss-makers) |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Run the screener

```bash
# Screen all Nordic exchanges
python -m src.main scan

# Screen specific exchanges
python -m src.main scan -e oslo -e stockholm

# Specify output file
python -m src.main scan -o my_report.pdf

# Include top N companies (default: 10)
python -m src.main scan --top 20

# Bypass cache
python -m src.main scan --no-cache
```

### View criteria

```bash
python -m src.main info
```

### Clear cache

```bash
python -m src.main clear-cache
```

## Output

The screener generates a PDF report containing:
- Summary of screening results
- Top N undervalued companies ranked by composite score
- Detailed analysis for each company showing all filter results

Reports are saved to `data/output/nordic_screen_YYYY-MM-DD.pdf` by default.

## Data Sources

- **Company Lists**: Euronext API (Oslo), Nasdaq Nordic (Stockholm/Copenhagen)
- **Financial Data**: Yahoo Finance via `yfinance`
- **Industry Classification**: Yahoo Finance sector/industry data

## Architecture

```
StockScreen/
├── src/
│   ├── main.py                     # CLI entry point
│   ├── config.py                   # Configuration & settings
│   ├── data/
│   │   ├── company_fetcher.py      # Exchange company lists
│   │   ├── financial_fetcher.py    # yfinance data fetching
│   │   └── cache_manager.py        # Data caching (diskcache)
│   ├── calculations/
│   │   ├── metrics.py              # PE, ROIC, D/E, FCF
│   │   ├── ttm_calculator.py       # TTM from quarterly data
│   │   ├── growth_analyzer.py      # Growth consistency
│   │   └── industry_averages.py    # Industry PE averages
│   ├── screening/
│   │   ├── filters.py              # Individual filters
│   │   └── screener.py             # Orchestrator
│   └── output/
│       ├── pdf_generator.py        # PDF report (fpdf2)
│       └── templates/
│           └── report_template.html
├── data/
│   ├── cache/
│   └── output/
├── requirements.txt
└── README.md
```

## License

MIT
