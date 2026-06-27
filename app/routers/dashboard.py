"""The MIS / business layer: an operator dashboard.

This is the "management information system" half of the project. It surfaces the
metrics you run the business on — usage, customers by tier, estimated MRR, data
coverage/freshness, and the largest companies in your dataset — in one view.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

from ..auth import require_admin
from ..config import settings
from ..db import get_session
from ..models import ApiKey, Company, Financials, Usage

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


def _top_companies_by_revenue(session: Session, limit: int = 10) -> list:
    rows = []
    for company in session.exec(select(Company)).all():
        latest = session.exec(
            select(Financials)
            .where(Financials.cik == company.cik)
            .order_by(Financials.fiscal_year.desc())
            .limit(1)
        ).first()
        if latest and latest.revenue is not None:
            rows.append(
                {
                    "ticker": company.ticker,
                    "fiscal_year": latest.fiscal_year,
                    "revenue_b": round(latest.revenue / 1e9, 1),
                    "net_margin": latest.net_margin,
                    "revenue_growth": latest.revenue_growth,
                }
            )
    rows.sort(key=lambda r: r["revenue_b"], reverse=True)
    return rows[:limit]


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    token: Optional[str] = None,
    session: Session = Depends(get_session),
):
    require_admin(token)
    today = date.today()

    total_keys = session.exec(select(func.count()).select_from(ApiKey)).one()
    pro_keys = session.exec(
        select(func.count()).select_from(ApiKey).where(ApiKey.tier == "pro")
    ).one()
    calls_today = session.exec(
        select(func.coalesce(func.sum(Usage.count), 0)).where(Usage.day == today)
    ).one()
    calls_total = session.exec(select(func.coalesce(func.sum(Usage.count), 0))).one()
    companies_covered = session.exec(select(func.count()).select_from(Company)).one()
    financial_rows = session.exec(select(func.count()).select_from(Financials)).one()
    last_fetch = session.exec(select(func.max(Company.fetched_at))).one()

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "total_keys": total_keys,
            "pro_keys": pro_keys,
            "free_keys": total_keys - pro_keys,
            "calls_today": calls_today,
            "calls_total": calls_total,
            "estimated_mrr": f"{pro_keys * settings.pro_price_usd:,.0f}",
            "companies_covered": companies_covered,
            "financial_rows": financial_rows,
            "last_fetch": last_fetch.isoformat(timespec="minutes") if last_fetch else "never",
            "top": _top_companies_by_revenue(session),
        },
    )
