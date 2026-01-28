"""Calculates and manages industry average PE ratios."""

from typing import Optional
from collections import defaultdict

from ..data.cache_manager import cache


class IndustryAverages:
    """Manages industry and sector average PE calculations."""

    def __init__(self):
        self._pe_by_industry: dict[str, list[float]] = defaultdict(list)
        self._pe_by_sector: dict[str, list[float]] = defaultdict(list)
        self._averages_calculated = False
        self._industry_avg: dict[str, float] = {}
        self._sector_avg: dict[str, float] = {}

    def add_company(self, industry: Optional[str], sector: Optional[str], pe: Optional[float]) -> None:
        """Add a company's PE to the calculation pool."""
        if pe is None or pe <= 0 or pe > 200:  # Filter outliers
            return

        if industry:
            self._pe_by_industry[industry].append(pe)

        if sector:
            self._pe_by_sector[sector].append(pe)

        self._averages_calculated = False

    def _calculate_averages(self) -> None:
        """Calculate averages from collected data."""
        for industry, pes in self._pe_by_industry.items():
            if pes:
                # Use median to reduce outlier impact
                sorted_pes = sorted(pes)
                mid = len(sorted_pes) // 2
                if len(sorted_pes) % 2 == 0:
                    self._industry_avg[industry] = (sorted_pes[mid - 1] + sorted_pes[mid]) / 2
                else:
                    self._industry_avg[industry] = sorted_pes[mid]

        for sector, pes in self._pe_by_sector.items():
            if pes:
                sorted_pes = sorted(pes)
                mid = len(sorted_pes) // 2
                if len(sorted_pes) % 2 == 0:
                    self._sector_avg[sector] = (sorted_pes[mid - 1] + sorted_pes[mid]) / 2
                else:
                    self._sector_avg[sector] = sorted_pes[mid]

        self._averages_calculated = True

        # Cache the results
        cache.set_industry_averages({
            "industry": self._industry_avg,
            "sector": self._sector_avg
        })

    def get_industry_average(self, industry: Optional[str]) -> Optional[float]:
        """Get average PE for an industry."""
        if not self._averages_calculated:
            self._calculate_averages()

        if not industry:
            return None

        return self._industry_avg.get(industry)

    def get_sector_average(self, sector: Optional[str]) -> Optional[float]:
        """Get average PE for a sector."""
        if not self._averages_calculated:
            self._calculate_averages()

        if not sector:
            return None

        return self._sector_avg.get(sector)

    def get_peer_average(self, industry: Optional[str], sector: Optional[str]) -> Optional[float]:
        """
        Get peer average PE, preferring industry over sector.

        Args:
            industry: Company's industry
            sector: Company's sector

        Returns:
            Industry average if available, otherwise sector average
        """
        industry_avg = self.get_industry_average(industry)
        if industry_avg is not None:
            return industry_avg

        return self.get_sector_average(sector)

    def is_below_average(self, pe: Optional[float], industry: Optional[str], sector: Optional[str]) -> Optional[bool]:
        """
        Check if PE is below peer average.

        Returns:
            True if below average, False if above, None if can't determine
        """
        if pe is None or pe <= 0:
            return None

        peer_avg = self.get_peer_average(industry, sector)
        if peer_avg is None:
            return None

        return pe < peer_avg

    def get_all_averages(self) -> dict:
        """Get all calculated averages."""
        if not self._averages_calculated:
            self._calculate_averages()

        return {
            "industry": self._industry_avg.copy(),
            "sector": self._sector_avg.copy()
        }

    def load_from_cache(self) -> bool:
        """Load cached averages if available."""
        cached = cache.get_industry_averages()
        if cached:
            self._industry_avg = cached.get("industry", {})
            self._sector_avg = cached.get("sector", {})
            self._averages_calculated = True
            return True
        return False
