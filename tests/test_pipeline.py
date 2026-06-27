from app.pipeline.enrich import extract_annual_series, parse_company_facts

# A minimal slice of SEC companyfacts JSON, shaped like the real thing.
US_GAAP = {
    "Revenues": {
        "units": {
            "USD": [
                {"fy": 2022, "fp": "FY", "form": "10-K", "end": "2022-12-31", "val": 1000},
                {"fy": 2023, "fp": "FY", "form": "10-K", "end": "2023-12-31", "val": 1200},
                # quarterly + non-10-K entries must be ignored:
                {"fy": 2023, "fp": "Q3", "form": "10-Q", "end": "2023-09-30", "val": 300},
            ]
        }
    },
    "NetIncomeLoss": {
        "units": {
            "USD": [
                {"fy": 2022, "fp": "FY", "form": "10-K", "end": "2022-12-31", "val": 100},
                {"fy": 2023, "fp": "FY", "form": "10-K", "end": "2023-12-31", "val": 180},
            ]
        }
    },
    "StockholdersEquity": {
        "units": {
            "USD": [
                {"fy": 2023, "fp": "FY", "form": "10-K", "end": "2023-12-31", "val": 900},
            ]
        }
    },
}


def test_extract_annual_series_keeps_only_annual_10k():
    series = extract_annual_series(US_GAAP, ["Revenues"])
    assert series == {2022: 1000.0, 2023: 1200.0}  # the 10-Q is excluded


def test_extract_annual_series_falls_back_through_concepts():
    # First concept missing -> should fall through to the second.
    series = extract_annual_series(US_GAAP, ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"])
    assert series[2023] == 1200.0


def test_parse_company_facts_computes_metrics():
    rows = parse_company_facts({"facts": {"us-gaap": US_GAAP}})
    by_year = {r["fiscal_year"]: r for r in rows}

    fy23 = by_year[2023]
    assert fy23["revenue"] == 1200.0
    assert fy23["net_margin"] == 0.15            # 180 / 1200
    assert fy23["revenue_growth"] == 0.2         # (1200 - 1000) / 1000
    assert fy23["roe"] == 0.2                     # 180 / 900

    # 2022 has no prior year -> growth is undefined
    assert by_year[2022]["revenue_growth"] is None
