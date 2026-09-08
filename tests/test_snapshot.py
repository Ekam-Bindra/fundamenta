from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Company, Financials
from app.snapshot import export_snapshot, load_snapshot


def _fresh_engine(tmp_path, name):
    eng = create_engine(f"sqlite:///{tmp_path}/{name}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    return eng


def test_snapshot_export_then_load_roundtrip(tmp_path):
    src = _fresh_engine(tmp_path, "src.db")
    with Session(src) as s:
        s.add(Company(cik=320193, ticker="AAPL", name="Apple Inc."))
        s.add(
            Financials(
                cik=320193, ticker="AAPL", fiscal_year=2024,
                revenue=391035000000.0, net_income=93736000000.0,
                net_margin=0.2397, revenue_growth=0.0202, roe=1.6459,
            )
        )
        s.commit()
        path = str(tmp_path / "fundamentals.json")
        assert export_snapshot(s, path) == 1  # one company

    # Load into a completely separate DB and verify fidelity.
    dst = _fresh_engine(tmp_path, "dst.db")
    with Session(dst) as s:
        assert load_snapshot(s, path) == 1  # one financial row
        row = s.exec(select(Financials)).one()
        assert row.ticker == "AAPL"
        assert row.revenue == 391035000000.0
        assert row.net_margin == 0.2397


def test_load_snapshot_missing_file_is_noop(tmp_path):
    dst = _fresh_engine(tmp_path, "empty.db")
    with Session(dst) as s:
        assert load_snapshot(s, str(tmp_path / "nope.json")) == 0
