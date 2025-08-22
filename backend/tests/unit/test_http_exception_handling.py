from fastapi import HTTPException
from fastapi.testclient import TestClient


def test_http_exception_returns_json_and_status(test_app):
    # Add a test route that raises a 400 HTTPException with a simple detail
    async def raise_400():
        raise HTTPException(status_code=400, detail="Bad request example")

    test_app.add_api_route("/test/raise400", raise_400, methods=["GET"])  # type: ignore[arg-type]

    client = TestClient(test_app)

    resp = client.get("/test/raise400")
    assert resp.status_code == 400
    assert resp.headers.get("content-type", "").startswith("application/json")
    assert resp.json() == {"detail": "Bad request example"}


def test_http_exception_includes_headers(test_app):
    # Add a test route that raises 429 with Retry-After header
    async def raise_429():
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
            headers={"Retry-After": "7"},
        )

    test_app.add_api_route("/test/raise429", raise_429, methods=["GET"])  # type: ignore[arg-type]

    client = TestClient(test_app)

    resp = client.get("/test/raise429")
    assert resp.status_code == 429
    assert resp.json() == {"detail": "Too many requests"}
    # FastAPI should propagate headers provided to HTTPException
    assert resp.headers.get("Retry-After") == "7"
