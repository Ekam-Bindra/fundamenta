"""Database tables.

The schema is split into two halves:

* The *product* tables (Company, Financials) hold the data you sell. They are
  niche-specific — swap them when you change source. The current niche is
  company fundamentals derived from SEC EDGAR XBRL filings.
* The *business* tables (ApiKey, Usage) power auth, rate-limiting, billing, and
  the MIS dashboard. These stay the same for any data API.
"""

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


# --- Product data (niche-specific: SEC fundamentals) ----------------------
class Company(SQLModel, table=True):
    """A company we cover, keyed by its SEC Central Index Key (CIK)."""

    cik: int = Field(primary_key=True)
    ticker: str = Field(index=True)
    name: str = ""
    sic: Optional[str] = None  # SEC industry classification code
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class Financials(SQLModel, table=True):
    """One row per (company, fiscal year): raw XBRL facts + computed metrics."""

    id: Optional[int] = Field(default=None, primary_key=True)
    cik: int = Field(index=True)
    ticker: str = Field(index=True)
    fiscal_year: int = Field(index=True)

    # Raw annual facts (USD), pulled from 10-K filings.
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    assets: Optional[float] = None
    liabilities: Optional[float] = None
    equity: Optional[float] = None

    # Computed by the enrichment step (the data-science value-add).
    net_margin: Optional[float] = None       # net_income / revenue
    revenue_growth: Optional[float] = None   # YoY change in revenue
    roe: Optional[float] = None              # net_income / equity

    computed_at: datetime = Field(default_factory=datetime.utcnow)


# --- Business data (generic) ----------------------------------------------
class ApiKey(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    name: str = "anonymous"
    tier: str = "free"  # "free" | "pro"
    active: bool = True
    source: str = "self-serve"  # "self-serve" | "rapidapi" | "stripe"
    stripe_customer_id: Optional[str] = Field(default=None, index=True)
    stripe_subscription_id: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Usage(SQLModel, table=True):
    """One row per (key, day) holding that day's request count for rate-limiting."""

    id: Optional[int] = Field(default=None, primary_key=True)
    api_key_id: int = Field(index=True)
    day: date = Field(index=True)
    count: int = 0
