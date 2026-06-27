"""Public self-serve signup page.

Serves a small HTML page that lets a visitor mint a free API key (via the
existing POST /v1/keys endpoint) and, when a Stripe Payment Link is configured
(STRIPE_PAYMENT_LINK), upgrade to the paid tier — passing the new key to Stripe
checkout as the `client_reference_id` so the webhook can upgrade it on payment.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import settings

router = APIRouter(tags=["signup"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/signup", response_class=HTMLResponse)
def signup(request: Request):
    return templates.TemplateResponse(
        request,
        "signup.html",
        {
            "service_name": "Company Fundamentals API",
            "free_limit": settings.free_daily_limit,
            "pro_limit": settings.pro_daily_limit,
            "pro_price": f"{settings.pro_price_usd:,.0f}",
            "payment_link": settings.stripe_payment_link,
        },
    )
