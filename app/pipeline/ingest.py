"""Step 1 of the data pipeline: pull raw filings from SEC EDGAR.

Source: SEC EDGAR (data.sec.gov / sec.gov), free and in the public domain.
Docs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces

SEC requires a descriptive User-Agent with real contact info (set SEC_USER_AGENT)
and limits clients to <10 requests/second; we sleep between calls to stay polite.

To change niche, replace this collector with your own and keep store_companies'
shape, or swap the product tables entirely.
"""

import asyncio
from datetime import datetime

import httpx
from sqlmodel import Session, delete

from ..config import settings
from ..models import Company, Financials
from .enrich import parse_company_facts

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"


def _headers() -> dict:
    return {"User-Agent": settings.sec_user_agent, "Accept-Encoding": "gzip, deflate"}


async def fetch_ticker_map(client: httpx.AsyncClient) -> dict:
    """Return {TICKER: (cik:int, name:str)} from SEC's master ticker file."""
    resp = await client.get(TICKERS_URL)
    resp.raise_for_status()
    data = resp.json()
    return {
        str(row["ticker"]).upper(): (int(row["cik_str"]), row.get("title", ""))
        for row in data.values()
    }


async def fetch_company_facts(client: httpx.AsyncClient, cik: int):
    resp = await client.get(FACTS_URL.format(cik=cik))
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


async def collect(tickers: list) -> list:
    """Fetch ticker->CIK map, then company facts for each covered ticker."""
    collected = []
    async with httpx.AsyncClient(timeout=30.0, headers=_headers()) as client:
        ticker_map = await fetch_ticker_map(client)
        for ticker in tickers:
            ticker = ticker.strip().upper()
            if not ticker or ticker not in ticker_map:
                continue
            cik, name = ticker_map[ticker]
            try:
                facts = await fetch_company_facts(client, cik)
            except Exception:
                facts = None
            if facts:
                collected.append({"ticker": ticker, "cik": cik, "name": name, "facts": facts})
            await asyncio.sleep(0.2)  # stay well under SEC's 10 req/s limit
    return collected


def store_companies(session: Session, collected: list) -> tuple:
    """Upsert companies and replace their financials. Returns (companies, rows)."""
    n_companies = 0
    n_rows = 0
    for item in collected:
        company = session.get(Company, item["cik"]) or Company(cik=item["cik"])
        company.ticker = item["ticker"]
        company.name = item["name"]
        company.fetched_at = datetime.utcnow()
        session.add(company)
        n_companies += 1

        # Rebuild this company's financials from scratch.
        session.exec(delete(Financials).where(Financials.cik == item["cik"]))
        for row in parse_company_facts(item["facts"]):
            session.add(Financials(cik=item["cik"], ticker=item["ticker"], **row))
            n_rows += 1
    session.commit()
    return n_companies, n_rows
