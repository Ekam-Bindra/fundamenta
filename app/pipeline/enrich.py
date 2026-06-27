"""Step 2 of the data pipeline: the data-science layer.

Turns raw SEC XBRL company-facts JSON into the product we sell: a clean,
per-fiscal-year table of fundamentals plus computed metrics (margins, growth,
return on equity). The extraction/compute functions are pure and unit-tested so
the modeling logic is verifiable independent of the network and database.

XBRL background: a company reports the same concept (e.g. revenue) under
different US-GAAP tags over the years, so we try a priority list of tags and use
the first that yields annual (10-K, full-year) data.
"""

from typing import Optional

# US-GAAP concept tags, in priority order, for each metric we extract.
REVENUE_CONCEPTS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
]
NET_INCOME_CONCEPTS = ["NetIncomeLoss"]
ASSETS_CONCEPTS = ["Assets"]
LIABILITIES_CONCEPTS = ["Liabilities"]
EQUITY_CONCEPTS = [
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
]


def extract_annual_series(us_gaap: dict, concepts: list) -> dict:
    """Return {fiscal_year: value} for the first concept that has 10-K/FY data."""
    for concept in concepts:
        node = us_gaap.get(concept)
        if not node:
            continue
        units = node.get("units", {})
        entries = units.get("USD")
        if entries is None:
            entries = next(iter(units.values()), [])

        series: dict = {}
        best_end: dict = {}
        for entry in entries:
            if entry.get("fp") != "FY":
                continue
            if not str(entry.get("form", "")).startswith("10-K"):
                continue
            fy = entry.get("fy")
            val = entry.get("val")
            end = entry.get("end", "")
            if fy is None or val is None:
                continue
            # Prefer the most recently-ending period for a given fiscal year.
            if fy not in series or end > best_end.get(fy, ""):
                series[fy] = float(val)
                best_end[fy] = end
        if series:
            return series
    return {}


def _ratio(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or not denominator:
        return None
    return round(numerator / denominator, 4)


def parse_company_facts(facts_json: dict) -> list:
    """Build a list of per-fiscal-year fundamentals dicts from companyfacts JSON."""
    us_gaap = (facts_json.get("facts") or {}).get("us-gaap") or {}
    revenue = extract_annual_series(us_gaap, REVENUE_CONCEPTS)
    net_income = extract_annual_series(us_gaap, NET_INCOME_CONCEPTS)
    assets = extract_annual_series(us_gaap, ASSETS_CONCEPTS)
    liabilities = extract_annual_series(us_gaap, LIABILITIES_CONCEPTS)
    equity = extract_annual_series(us_gaap, EQUITY_CONCEPTS)

    years = sorted(set(revenue) | set(net_income) | set(assets) | set(equity))
    rows = []
    for year in years:
        rev = revenue.get(year)
        ni = net_income.get(year)
        eq = equity.get(year)
        prev_rev = revenue.get(year - 1)
        rows.append(
            {
                "fiscal_year": year,
                "revenue": rev,
                "net_income": ni,
                "assets": assets.get(year),
                "liabilities": liabilities.get(year),
                "equity": eq,
                "net_margin": _ratio(ni, rev),
                "revenue_growth": _ratio(rev - prev_rev, prev_rev) if rev is not None and prev_rev else None,
                "roe": _ratio(ni, eq),
            }
        )
    return rows
