from app.config import settings


def test_coverage_list_defaults_to_inline_tickers():
    assert "AAPL" in settings.coverage_list
    assert all(t == t.upper() for t in settings.coverage_list)


def test_coverage_file_takes_precedence(tmp_path, monkeypatch):
    f = tmp_path / "tickers.txt"
    f.write_text("# a comment\nAAPL\nmsft\n\nbrk-b\n")
    monkeypatch.setattr(settings, "coverage_file", str(f))

    assert settings.coverage_list == ["AAPL", "MSFT", "BRK-B"]  # uppercased, comments/blanks skipped


def test_missing_coverage_file_falls_back_to_inline(monkeypatch):
    monkeypatch.setattr(settings, "coverage_file", "/no/such/file.txt")
    assert "AAPL" in settings.coverage_list  # graceful fallback, no crash
