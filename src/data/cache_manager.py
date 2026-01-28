"""Cache manager using diskcache for persistent caching."""

import hashlib
from typing import Any, Optional
from diskcache import Cache
from ..config import settings


class CacheManager:
    """Manages disk-based caching for financial data."""

    def __init__(self):
        settings.ensure_dirs()
        self._cache = Cache(
            str(settings.cache_dir),
            size_limit=settings.cache.max_size_mb * 1024 * 1024
        )
        self._ttl_seconds = settings.cache.ttl_hours * 3600

    def _make_key(self, prefix: str, identifier: str) -> str:
        """Create a cache key from prefix and identifier."""
        return f"{prefix}:{identifier}"

    def get(self, prefix: str, identifier: str) -> Optional[Any]:
        """Retrieve item from cache."""
        key = self._make_key(prefix, identifier)
        return self._cache.get(key)

    def set(self, prefix: str, identifier: str, value: Any) -> None:
        """Store item in cache with TTL."""
        key = self._make_key(prefix, identifier)
        self._cache.set(key, value, expire=self._ttl_seconds)

    def get_company_list(self, exchange: str) -> Optional[list[dict]]:
        """Get cached company list for an exchange."""
        return self.get("companies", exchange)

    def set_company_list(self, exchange: str, companies: list[dict]) -> None:
        """Cache company list for an exchange."""
        self.set("companies", exchange, companies)

    def get_financials(self, ticker: str) -> Optional[dict]:
        """Get cached financial data for a ticker."""
        return self.get("financials", ticker)

    def set_financials(self, ticker: str, data: dict) -> None:
        """Cache financial data for a ticker."""
        self.set("financials", ticker, data)

    def get_industry_averages(self) -> Optional[dict]:
        """Get cached industry averages."""
        return self.get("industry", "averages")

    def set_industry_averages(self, averages: dict) -> None:
        """Cache industry averages."""
        self.set("industry", "averages", averages)

    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()

    def close(self) -> None:
        """Close the cache connection."""
        self._cache.close()


# Global cache instance
cache = CacheManager()
