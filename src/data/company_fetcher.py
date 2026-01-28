"""Fetches company lists from Nordic stock exchanges."""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
from typing import Optional
from rich.console import Console

from ..config import settings
from .cache_manager import cache

console = Console()


class CompanyFetcher:
    """Fetches and parses company lists from Nordic exchanges."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def fetch_oslo(self) -> list[dict]:
        """Fetch companies from Oslo Bors (Euronext)."""
        cached = cache.get_company_list("oslo")
        if cached:
            return cached

        url = settings.exchanges["oslo"].url
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Parse CSV response
            df = pd.read_csv(StringIO(response.text), sep=";")
            companies = []

            for _, row in df.iterrows():
                symbol = str(row.get("Symbol", row.get("symbol", ""))).strip()
                name = str(row.get("Name", row.get("name", ""))).strip()

                if symbol and symbol != "nan":
                    companies.append({
                        "symbol": symbol,
                        "name": name,
                        "exchange": "oslo",
                        "ticker": f"{symbol}.OL"
                    })

            cache.set_company_list("oslo", companies)
            return companies

        except Exception as e:
            console.print(f"[yellow]Warning: Could not fetch Oslo companies: {e}[/yellow]")
            return self._get_oslo_fallback()

    def _get_oslo_fallback(self) -> list[dict]:
        """Fallback list of major Oslo Bors companies."""
        symbols = [
            ("EQNR", "Equinor"),
            ("DNB", "DNB Bank"),
            ("TEL", "Telenor"),
            ("MOWI", "Mowi"),
            ("ORK", "Orkla"),
            ("YAR", "Yara International"),
            ("SALM", "SalMar"),
            ("AKRBP", "Aker BP"),
            ("NHY", "Norsk Hydro"),
            ("SUBC", "Subsea 7"),
            ("TOM", "Tomra Systems"),
            ("AKSO", "Aker Solutions"),
            ("KOG", "Kongsberg Gruppen"),
            ("SCATC", "Scatec"),
            ("BWO", "BW Offshore"),
        ]
        return [
            {"symbol": s, "name": n, "exchange": "oslo", "ticker": f"{s}.OL"}
            for s, n in symbols
        ]

    def fetch_nasdaq_nordic(self, exchange: str) -> list[dict]:
        """Fetch companies from Nasdaq Nordic (Stockholm/Copenhagen)."""
        cached = cache.get_company_list(exchange)
        if cached:
            return cached

        suffix = settings.exchanges[exchange].suffix

        # Use Nasdaq Nordic API
        market_map = {
            "stockholm": "XSTO",
            "copenhagen": "XCSE"
        }
        market = market_map.get(exchange, "XSTO")

        url = f"https://api.nasdaq.com/api/nordic/instruments"
        params = {
            "assetClass": "shares",
            "market": market
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            companies = []
            rows = data.get("data", {}).get("rows", [])

            for row in rows:
                symbol = row.get("symbol", "").strip()
                name = row.get("name", "").strip()

                if symbol:
                    companies.append({
                        "symbol": symbol,
                        "name": name,
                        "exchange": exchange,
                        "ticker": f"{symbol}{suffix}"
                    })

            if companies:
                cache.set_company_list(exchange, companies)
                return companies

        except Exception as e:
            console.print(f"[yellow]Warning: API fetch failed for {exchange}: {e}[/yellow]")

        # Fallback to scraping
        return self._fetch_nasdaq_scrape(exchange)

    def _fetch_nasdaq_scrape(self, exchange: str) -> list[dict]:
        """Fallback: scrape Nasdaq Nordic website."""
        url = settings.exchanges[exchange].url
        suffix = settings.exchanges[exchange].suffix

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            companies = []

            # Try to find company table
            table = soup.find("table", {"class": lambda x: x and "tablesorter" in x})
            if table:
                for row in table.find_all("tr")[1:]:  # Skip header
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        symbol = cells[1].get_text(strip=True)
                        name = cells[0].get_text(strip=True)
                        if symbol:
                            companies.append({
                                "symbol": symbol,
                                "name": name,
                                "exchange": exchange,
                                "ticker": f"{symbol}{suffix}"
                            })

            if companies:
                cache.set_company_list(exchange, companies)
                return companies

        except Exception as e:
            console.print(f"[yellow]Warning: Scraping failed for {exchange}: {e}[/yellow]")

        return self._get_nordic_fallback(exchange)

    def _get_nordic_fallback(self, exchange: str) -> list[dict]:
        """Fallback list of Nordic companies (expanded)."""
        suffix = settings.exchanges[exchange].suffix

        if exchange == "stockholm":
            symbols = [
                # Large Cap
                ("VOLV-B", "Volvo"),
                ("ERIC-B", "Ericsson"),
                ("ATCO-A", "Atlas Copco A"),
                ("ATCO-B", "Atlas Copco B"),
                ("ASSA-B", "Assa Abloy"),
                ("SEB-A", "SEB"),
                ("SWED-A", "Swedbank"),
                ("HM-B", "H&M"),
                ("SAND", "Sandvik"),
                ("SKF-B", "SKF"),
                ("INVE-B", "Investor"),
                ("SHB-A", "Handelsbanken"),
                ("ESSITY-B", "Essity"),
                ("HEXA-B", "Hexagon"),
                ("ALFA", "Alfa Laval"),
                ("ELUX-B", "Electrolux"),
                ("TEL2-B", "Tele2"),
                ("KINV-B", "Kinnevik"),
                ("BOL", "Boliden"),
                ("SSAB-A", "SSAB"),
                ("TELIA", "Telia"),
                ("NIBE-B", "NIBE Industrier"),
                ("SWMA", "Swedish Match"),
                ("GETI-B", "Getinge"),
                ("SECU-B", "Securitas"),
                ("LATO-B", "Latour"),
                ("SAAB-B", "Saab"),
                ("LIFCO-B", "Lifco"),
                ("SOBI", "Swedish Orphan Biovitrum"),
                ("EVO", "Evolution"),
                # Mid Cap
                ("BETS-B", "Betsson"),
                ("ADDV-B", "AddLife"),
                ("DUNI", "Duni"),
                ("EPRO-B", "Elekta"),
                ("HUFV-A", "Hufvudstaden"),
                ("HUSQ-B", "Husqvarna"),
                ("INTRUM", "Intrum"),
                ("JM", "JM"),
                ("LUND-B", "Lundbergforetagen"),
                ("MYCR", "Mycronic"),
                ("NCC-B", "NCC"),
                ("PEAB-B", "Peab"),
                ("RATO-B", "Ratos"),
                ("RESURS", "Resurs Holding"),
                ("SECT-B", "Sectra"),
                ("STE-R", "Storskogen"),
                ("SWEC-B", "Sweco"),
                ("TREL-B", "Trelleborg"),
                ("WIHL", "Wihlborgs"),
            ]
        else:  # copenhagen
            symbols = [
                # Large Cap
                ("NOVO-B", "Novo Nordisk"),
                ("MAERSK-B", "Maersk"),
                ("CARL-B", "Carlsberg"),
                ("VWS", "Vestas Wind"),
                ("COLO-B", "Coloplast"),
                ("DSV", "DSV"),
                ("NZYM-B", "Novozymes"),
                ("ORSTED", "Orsted"),
                ("DANSKE", "Danske Bank"),
                ("PNDORA", "Pandora"),
                ("GN", "GN Store Nord"),
                ("DEMANT", "Demant"),
                ("ROCK-B", "Rockwool"),
                ("FLS", "FLSmidth"),
                ("TRYG", "Tryg"),
                ("GMAB", "Genmab"),
                ("AMBU-B", "Ambu"),
                ("JYSK", "Jyske Bank"),
                ("RBREW", "Royal Unibrew"),
                ("SIM", "SimCorp"),
                ("ISS", "ISS"),
                ("DFDS", "DFDS"),
                ("TOP", "Topdanmark"),
                ("CHR", "Chr Hansen"),
                ("BAVA", "Bavarian Nordic"),
                # Mid Cap
                ("ALK-B", "ALK-Abello"),
                ("ATEA", "Atea"),
                ("CBRAIN", "cBrain"),
                ("CPHCAP", "Copenhagen Capital"),
                ("DNORD", "D/S Norden"),
                ("GREEN", "GreenMobility"),
                ("HARB-B", "Harboes Bryggeri"),
                ("NKT", "NKT"),
                ("NNIT", "NNIT"),
                ("PAAL-B", "Per Aarsleff"),
                ("RTX", "RTX"),
                ("SCHOUW", "Schouw"),
                ("SPNO", "Spar Nord"),
                ("SYDB", "Sydbank"),
                ("VIA", "Via Equity"),
                ("ZEAL", "Zealand Pharma"),
            ]

        return [
            {"symbol": s, "name": n, "exchange": exchange, "ticker": f"{s}{suffix}"}
            for s, n in symbols
        ]

    def fetch_all(self) -> list[dict]:
        """Fetch companies from all Nordic exchanges."""
        all_companies = []

        console.print("[blue]Fetching Oslo Bors companies...[/blue]")
        all_companies.extend(self.fetch_oslo())

        console.print("[blue]Fetching Stockholm companies...[/blue]")
        all_companies.extend(self.fetch_nasdaq_nordic("stockholm"))

        console.print("[blue]Fetching Copenhagen companies...[/blue]")
        all_companies.extend(self.fetch_nasdaq_nordic("copenhagen"))

        console.print(f"[green]Total companies: {len(all_companies)}[/green]")
        return all_companies
