"""The product endpoints — clean company fundamentals from SEC filings.

Every route here is metered via the `get_api_key` dependency. This is what
customers pay to call.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..auth import get_api_key
from ..db import get_session
from ..models import ApiKey, Company, Financials

router = APIRouter(prefix="/v1", tags=["companies"])


def _fin_dict(row: Financials) -> dict:
    return {
        "fiscal_year": row.fiscal_year,
        "revenue": row.revenue,
        "net_income": row.net_income,
        "assets": row.assets,
        "liabilities": row.liabilities,
        "equity": row.equity,
        "net_margin": row.net_margin,
        "revenue_growth": row.revenue_growth,
        "roe": row.roe,
    }


def _company_or_404(session: Session, ticker: str) -> Company:
    company = session.exec(
        select(Company).where(Company.ticker == ticker.upper())
    ).first()
    if company is None:
        raise HTTPException(status_code=404, detail=f"No coverage for ticker '{ticker.upper()}'")
    return company


@router.get("/companies")
def list_companies(
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session),
    _key: ApiKey = Depends(get_api_key),
):
    """List all companies currently covered."""
    rows = session.exec(select(Company).order_by(Company.ticker).limit(limit)).all()
    return {
        "count": len(rows),
        "results": [{"ticker": r.ticker, "cik": r.cik, "name": r.name} for r in rows],
    }


@router.get("/companies/{ticker}")
def get_company(
    ticker: str,
    session: Session = Depends(get_session),
    _key: ApiKey = Depends(get_api_key),
):
    """Company profile + its most recent fiscal year of fundamentals."""
    company = _company_or_404(session, ticker)
    latest = session.exec(
        select(Financials)
        .where(Financials.cik == company.cik)
        .order_by(Financials.fiscal_year.desc())
        .limit(1)
    ).first()
    return {
        "ticker": company.ticker,
        "cik": company.cik,
        "name": company.name,
        "latest": _fin_dict(latest) if latest else None,
    }


@router.get("/companies/{ticker}/fundamentals")
def fundamentals(
    ticker: str,
    session: Session = Depends(get_session),
    _key: ApiKey = Depends(get_api_key),
):
    """Full annual fundamentals time series for a company."""
    company = _company_or_404(session, ticker)
    rows = session.exec(
        select(Financials)
        .where(Financials.cik == company.cik)
        .order_by(Financials.fiscal_year)
    ).all()
    return {
        "ticker": company.ticker,
        "name": company.name,
        "fundamentals": [_fin_dict(r) for r in rows],
    }


@router.get("/screen")
def screen(
    min_revenue: float = Query(0, ge=0, description="Minimum latest-year revenue (USD)"),
    min_revenue_growth: Optional[float] = Query(
        None, description="Minimum latest-year YoY revenue growth, e.g. 0.1 = 10%"
    ),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
    _key: ApiKey = Depends(get_api_key),
):
    """Screen covered companies by their latest fiscal year's metrics."""
    results = []
    for company in session.exec(select(Company)).all():
        latest = session.exec(
            select(Financials)
            .where(Financials.cik == company.cik)
            .order_by(Financials.fiscal_year.desc())
            .limit(1)
        ).first()
        if latest is None or latest.revenue is None or latest.revenue < min_revenue:
            continue
        if min_revenue_growth is not None and (
            latest.revenue_growth is None or latest.revenue_growth < min_revenue_growth
        ):
            continue
        results.append({"ticker": company.ticker, "name": company.name, **_fin_dict(latest)})

    results.sort(key=lambda r: r["revenue"], reverse=True)
    results = results[:limit]
    return {"count": len(results), "results": results}
