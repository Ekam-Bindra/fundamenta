# Contributing to Fundamenta

Thanks for your interest in contributing! Fundamenta is an open-source template
for building a data-as-a-service API (SEC company fundamentals is the reference
implementation). Contributions of all kinds are welcome — bug fixes, new data
sources, docs, and tests.

## Getting started

```bash
git clone https://github.com/Ekam-Bindra/fundamenta.git
cd fundamenta
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# run the test suite
pytest -q

# run the API locally (loads the committed data snapshot — no DB needed)
uvicorn app.main:app --reload   # http://localhost:8000/docs
```

To refresh data from SEC (needs a real contact per SEC's fair-access policy):

```bash
SEC_USER_AGENT="Your Name you@example.com" python -m app.pipeline.run
```

## Project layout

- `app/` — FastAPI app: `main.py`, `routers/`, `auth.py`, `models.py`
- `app/pipeline/` — the data-science pipeline (`ingest.py`, `enrich.py`, `run.py`)
- `app/snapshot.py` — export/load the committed data snapshot (zero-signup mode)
- `tests/` — pytest suite
- Docs: `README.md`, `PLAN.md`, `LAUNCH.md`, `RUNBOOK_*.md`

## Development standards

- **Tests must pass:** `pytest -q`. Add tests for new behavior — the pipeline's
  pure functions (`enrich.py`, `snapshot.py`) are the easiest to cover.
- **Style:** we use [ruff](https://docs.astral.sh/ruff/) for linting/formatting.
  ```bash
  pip install ruff
  ruff check . && ruff format --check .
  ```
  Or install the git hook: `pip install pre-commit && pre-commit install`.
- Keep changes focused; match the surrounding style; prefer `Optional[...]` over
  `X | None` (the project supports Python 3.9+).

## Submitting a change

1. Fork the repo and create a branch: `git checkout -b fix/short-description`.
2. Make your change with tests; ensure `pytest -q` and `ruff check .` are clean.
3. Open a pull request describing **what** and **why**. Link any related issue.

## Reporting bugs / requesting features

Open an issue using the templates. For security issues, **do not** open a public
issue — see [SECURITY.md](SECURITY.md).

By contributing, you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
