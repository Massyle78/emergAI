"""Tests for structured error handlers."""

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _create_test_app() -> FastAPI:
    """Build a test app with error-triggering routes."""
    settings = Settings(app_env="testing")
    application = create_app(settings=settings)

    @application.get("/raise-404")
    async def raise_not_found():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Resource not found")

    @application.get("/raise-500")
    async def raise_unhandled():
        msg = "Something broke"
        raise RuntimeError(msg)

    @application.post("/validate")
    async def validate_body(request: Request):
        from pydantic import BaseModel, Field

        class Body(BaseModel):
            name: str = Field(..., min_length=1)

        Body.model_validate(await request.json())
        return {"ok": True}

    return application


class TestHttpExceptionHandler:
    def test_404_structured_response(self):
        client = TestClient(_create_test_app(), raise_server_exceptions=False)
        response = client.get("/raise-404")
        assert response.status_code == 404
        body = response.json()
        assert "error" in body
        assert body["error"]["status_code"] == 404
        assert body["error"]["detail"] == "Resource not found"

    def test_nonexistent_route_returns_structured_404(self):
        client = TestClient(_create_test_app(), raise_server_exceptions=False)
        response = client.get("/does-not-exist")
        assert response.status_code == 404
        body = response.json()
        assert "error" in body
        assert body["error"]["status_code"] == 404


class TestUnhandledExceptionHandler:
    def test_500_structured_response(self):
        client = TestClient(_create_test_app(), raise_server_exceptions=False)
        response = client.get("/raise-500")
        assert response.status_code == 500
        body = response.json()
        assert body["error"]["status_code"] == 500
        assert body["error"]["detail"] == "Internal server error"

    def test_500_does_not_leak_stack_trace(self):
        client = TestClient(_create_test_app(), raise_server_exceptions=False)
        response = client.get("/raise-500")
        body = response.json()
        assert "Traceback" not in str(body)
        assert "RuntimeError" not in str(body)


class TestValidationExceptionHandler:
    def test_422_structured_response(self):
        from pydantic import BaseModel, Field

        settings = Settings(app_env="testing")
        application = create_app(settings=settings)

        class StrictBody(BaseModel):
            name: str = Field(..., min_length=1)

        @application.post("/test-validation")
        async def endpoint(body: StrictBody):
            return {"name": body.name}

        client = TestClient(application, raise_server_exceptions=False)
        response = client.post("/test-validation", json={})
        assert response.status_code == 422
        body = response.json()
        assert "error" in body
        assert body["error"]["status_code"] == 422
        assert isinstance(body["error"]["detail"], list)


class TestErrorResponseFormat:
    def test_error_envelope_structure(self):
        client = TestClient(_create_test_app(), raise_server_exceptions=False)
        response = client.get("/raise-404")
        body = response.json()
        assert set(body.keys()) == {"error"}
        assert "status_code" in body["error"]
        assert "detail" in body["error"]
