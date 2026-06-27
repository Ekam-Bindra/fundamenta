"""Refresh app/data/sp500.txt from a public S&P 500 constituents dataset.

    python -m scripts.refresh_sp500

Source: the community-maintained `datasets/s-and-p-500-companies` repo. This is a
snapshot and may lag official S&P index changes — it is good enough for choosing
an API coverage universe, not for index-tracking. Tickers are normalized to SEC's
hyphen format (e.g. BRK.B -> BRK-B) so they match SEC's company_tickers.json.

Refuses to overwrite the file with an empty list if the fetch/parse fails.
"""

import csv
import io
import os

import httpx

SOURCES = [
    "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv",
    "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv",
]
OUT = "app/data/sp500.txt"


def _fetch() -> str:
    last_error = None
    for url in SOURCES:
        try:
            resp = httpx.get(url, timeout=30.0, follow_redirects=True)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:  # try the next mirror
            last_error = exc
    raise SystemExit(f"Could not fetch S&P 500 list from any source: {last_error}")


def main() -> None:
    reader = csv.DictReader(io.StringIO(_fetch()))
    tickers = []
    for row in reader:
        symbol = (row.get("Symbol") or row.get("symbol") or "").strip().upper()
        if symbol:
            tickers.append(symbol.replace(".", "-"))  # SEC uses hyphens
    tickers = sorted(set(tickers))
    if not tickers:
        raise SystemExit("Parsed 0 tickers — refusing to write an empty coverage file")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(f"# S&P 500 constituents — {len(tickers)} tickers\n")
        f.write(f"# source: {SOURCES[0]}\n")
        f.write("# community snapshot; may lag official index changes\n")
        f.write("# regenerate: python -m scripts.refresh_sp500\n")
        for ticker in tickers:
            f.write(ticker + "\n")
    print(f"wrote {len(tickers)} tickers to {OUT}")


if __name__ == "__main__":
    main()
