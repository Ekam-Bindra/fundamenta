from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_metered_endpoint_requires_auth():
    assert client.get("/v1/companies").status_code == 401


def test_self_serve_key_flow():
    signup = client.post("/v1/keys", params={"name": "pytest"})
    assert signup.status_code == 200
    api_key = signup.json()["api_key"]

    resp = client.get("/v1/companies", headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    assert "results" in resp.json()


def test_rapidapi_path_provisions_and_authorizes():
    headers = {
        "X-RapidAPI-Proxy-Secret": "test-proxy",
        "X-RapidAPI-User": "rapid-user-1",
        "X-RapidAPI-Subscription": "PRO",
    }
    assert client.get("/v1/companies", headers=headers).status_code == 200

    # Wrong proxy secret must be rejected.
    bad = dict(headers, **{"X-RapidAPI-Proxy-Secret": "nope"})
    assert client.get("/v1/companies", headers=bad).status_code == 403


def test_dashboard_requires_admin_token():
    assert client.get("/dashboard").status_code == 403
    assert client.get("/dashboard", params={"token": "test-admin"}).status_code == 200


def test_unknown_ticker_is_404():
    api_key = client.post("/v1/keys", params={"name": "pytest2"}).json()["api_key"]
    resp = client.get("/v1/companies/ZZZZ", headers={"X-API-Key": api_key})
    assert resp.status_code == 404


def test_signup_page_renders():
    resp = client.get("/signup")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "API key" in resp.text
    assert "/v1/keys" in resp.text  # the page wires up the mint call


def test_require_rapidapi_blocks_direct_traffic(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "require_rapidapi", True)  # auto-reverts after test

    # Direct self-serve traffic is now rejected, even with a valid key.
    api_key = client.post("/v1/keys", params={"name": "locked"}).json()["api_key"]
    blocked = client.get("/v1/companies", headers={"X-API-Key": api_key})
    assert blocked.status_code == 403
    assert "marketplace only" in blocked.json()["detail"]

    # RapidAPI-proxied traffic still works.
    headers = {
        "X-RapidAPI-Proxy-Secret": "test-proxy",
        "X-RapidAPI-User": "rapid-user-lock",
        "X-RapidAPI-Subscription": "PRO",
    }
    assert client.get("/v1/companies", headers=headers).status_code == 200
