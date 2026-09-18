from fastapi.testclient import TestClient

from backend.main import app, settings


def test_only_configured_frontend_origin_gets_cors_access() -> None:
    client = TestClient(app)
    headers = {
        "Origin": settings.frontend_url.rstrip("/"),
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    }
    allowed = client.options("/resumes", headers=headers)
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == settings.frontend_url.rstrip("/")

    denied = client.options("/resumes", headers={**headers, "Origin": "https://untrusted.example"})
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers
