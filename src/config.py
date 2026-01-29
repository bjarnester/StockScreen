"""Configuration and settings for Nordic Stock Screener."""

from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional


class ExchangeConfig(BaseModel):
    """Configuration for a stock exchange."""
    name: str
    suffix: str  # yfinance ticker suffix
    url: Optional[str] = None  # URL for fetching company list


class ScreeningThresholds(BaseModel):
    """Thresholds for screening criteria."""
    max_pe: float = Field(default=15.0, description="Maximum PE ratio")
    min_roic: float = Field(default=0.10, description="Minimum ROIC (10%)")
    roic_years: int = Field(default=3, description="Years of ROIC history required (yfinance typically has 4)")
    growth_years: int = Field(default=3, description="Years of consistent growth required")
    max_debt_to_equity: float = Field(default=1.0, description="Maximum D/E ratio")
    min_cf_yield: float = Field(default=0.05, description="Minimum FCF/Revenue (5%)")


class CacheConfig(BaseModel):
    """Cache configuration."""
    ttl_hours: int = Field(default=24, description="Cache TTL in hours")
    max_size_mb: int = Field(default=500, description="Max cache size in MB")


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    calls_per_minute: int = Field(default=30, description="Max API calls per minute")


class Settings(BaseModel):
    """Main application settings."""
    # Paths
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    cache_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data" / "cache")
    output_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data" / "output")

    # Exchanges
    exchanges: dict[str, ExchangeConfig] = Field(default_factory=lambda: {
        "oslo": ExchangeConfig(
            name="Oslo Bors",
            suffix=".OL",
            url="https://live.euronext.com/pd_es/data/stocks/download?mics=XOSL"
        ),
        "stockholm": ExchangeConfig(
            name="Nasdaq Stockholm",
            suffix=".ST",
            url="https://www.nasdaqomxnordic.com/shares/listed-companies/stockholm"
        ),
        "copenhagen": ExchangeConfig(
            name="Nasdaq Copenhagen",
            suffix=".CO",
            url="https://www.nasdaqomxnordic.com/shares/listed-companies/copenhagen"
        ),
    })

    # Thresholds
    thresholds: ScreeningThresholds = Field(default_factory=ScreeningThresholds)

    # Cache
    cache: CacheConfig = Field(default_factory=CacheConfig)

    # Rate limiting
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)

    def ensure_dirs(self) -> None:
        """Ensure all required directories exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
