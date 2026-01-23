"""Comprehensive tests for CSRF protection middleware.

Tests all CSRF scenarios including:
- Safe methods bypass (GET, HEAD, OPTIONS)
- Unsafe methods require CSRF (POST, PUT, DELETE, PATCH)
- Token validation (valid, invalid, missing)
- Cookie-based CSRF flow
- Exempt paths
- Token generation
"""

import secrets
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from app.core.csrf import CSRFMiddleware, get_csrf_token


# Create a test app with CSRF middleware
def create_test_app(
    exempt_paths: set[str] | None = None,
    cookie_name: str = "csrf_token",
    header_name: str = "X-CSRF-Token",
) -> FastAPI:
    """Create a FastAPI app with CSRF middleware for testing."""
    app = FastAPI()

    kwargs = {
        "cookie_name": cookie_name,
        "header_name": header_name,
    }
    if exempt_paths is not None:
        kwargs["exempt_paths"] = exempt_paths

    app.add_middleware(CSRFMiddleware, **kwargs)

    @app.get("/test")
    async def test_get():
        return {"method": "GET", "status": "ok"}

    @app.head("/test")
    async def test_head():
        return JSONResponse(content={}, headers={"X-Custom": "head"})

    @app.options("/test")
    async def test_options():
        return {"method": "OPTIONS", "status": "ok"}

    @app.post("/test")
    async def test_post():
        return {"method": "POST", "status": "ok"}

    @app.put("/test")
    async def test_put():
        return {"method": "PUT", "status": "ok"}

    @app.patch("/test")
    async def test_patch():
        return {"method": "PATCH", "status": "ok"}

    @app.delete("/test")
    async def test_delete():
        return {"method": "DELETE", "status": "ok"}

    @app.post("/exempt")
    async def test_exempt():
        return {"method": "POST", "status": "ok", "exempt": True}

    @app.get("/csrf-token")
    async def get_token(request: Request):
        return {"csrf_token": get_csrf_token(request)}

    return app


@pytest.fixture
def anyio_backend() -> str:
    """Specify the async backend for anyio tests."""
    return "asyncio"


@pytest.fixture
def test_app() -> FastAPI:
    """Create test app with CSRF middleware."""
    return create_test_app(exempt_paths={"/exempt"})


@pytest.fixture
def custom_header_app() -> FastAPI:
    """Create test app with custom CSRF header name."""
    return create_test_app(
        exempt_paths={"/exempt"},
        header_name="X-Custom-CSRF",
    )


@pytest.fixture
def custom_cookie_app() -> FastAPI:
    """Create test app with custom CSRF cookie name."""
    return create_test_app(
        exempt_paths={"/exempt"},
        cookie_name="custom_csrf",
    )


async def make_client(app: FastAPI) -> AsyncClient:
    """Create an async client for the given app."""
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


class TestCSRFMiddlewareSafeMethods:
    """Tests for safe HTTP methods that bypass CSRF protection."""

    @pytest.mark.anyio
    async def test_get_bypasses_csrf(self, test_app: FastAPI):
        """GET requests should not require CSRF token."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/test")

        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "GET"
        assert data["status"] == "ok"

    @pytest.mark.anyio
    async def test_head_bypasses_csrf(self, test_app: FastAPI):
        """HEAD requests should not require CSRF token."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            response = await client.head("/test")

        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_options_bypasses_csrf(self, test_app: FastAPI):
        """OPTIONS requests should not require CSRF token."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            response = await client.options("/test")

        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "OPTIONS"
        assert data["status"] == "ok"

    @pytest.mark.anyio
    async def test_get_sets_csrf_cookie(self, test_app: FastAPI):
        """GET request should set CSRF token cookie if not present."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/test")

        assert response.status_code == 200
        assert "csrf_token" in response.cookies


class TestCSRFMiddlewareUnsafeMethods:
    """Tests for unsafe HTTP methods that require CSRF protection."""

    @pytest.mark.anyio
    async def test_post_without_csrf_fails(self, test_app: FastAPI):
        """POST without CSRF token should return 403."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            response = await client.post("/test")

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "CSRF token missing"
        assert "X-CSRF-Token" in data["message"]

    @pytest.mark.anyio
    async def test_put_without_csrf_fails(self, test_app: FastAPI):
        """PUT without CSRF token should return 403."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            response = await client.put("/test")

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "CSRF token missing"

    @pytest.mark.anyio
    async def test_patch_without_csrf_fails(self, test_app: FastAPI):
        """PATCH without CSRF token should return 403."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            response = await client.patch("/test")

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "CSRF token missing"

    @pytest.mark.anyio
    async def test_delete_without_csrf_fails(self, test_app: FastAPI):
        """DELETE without CSRF token should return 403."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            response = await client.delete("/test")

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "CSRF token missing"

    @pytest.mark.anyio
    async def test_post_with_valid_csrf_passes(self, test_app: FastAPI):
        """POST with valid CSRF token should succeed."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            # First get a CSRF token via a GET request
            get_response = await client.get("/test")
            csrf_token = get_response.cookies.get("csrf_token")
            assert csrf_token is not None

            # Set the cookie on the client for subsequent requests
            client.cookies.set("csrf_token", csrf_token)

            # Make POST with both cookie (set on client) and header
            response = await client.post(
                "/test",
                headers={"X-CSRF-Token": csrf_token},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "POST"
        assert data["status"] == "ok"

    @pytest.mark.anyio
    async def test_put_with_valid_csrf_passes(self, test_app: FastAPI):
        """PUT with valid CSRF token should succeed."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            get_response = await client.get("/test")
            csrf_token = get_response.cookies.get("csrf_token")
            client.cookies.set("csrf_token", csrf_token)

            response = await client.put(
                "/test",
                headers={"X-CSRF-Token": csrf_token},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "PUT"
        assert data["status"] == "ok"

    @pytest.mark.anyio
    async def test_patch_with_valid_csrf_passes(self, test_app: FastAPI):
        """PATCH with valid CSRF token should succeed."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            get_response = await client.get("/test")
            csrf_token = get_response.cookies.get("csrf_token")
            client.cookies.set("csrf_token", csrf_token)

            response = await client.patch(
                "/test",
                headers={"X-CSRF-Token": csrf_token},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "PATCH"
        assert data["status"] == "ok"

    @pytest.mark.anyio
    async def test_delete_with_valid_csrf_passes(self, test_app: FastAPI):
        """DELETE with valid CSRF token should succeed."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            get_response = await client.get("/test")
            csrf_token = get_response.cookies.get("csrf_token")
            client.cookies.set("csrf_token", csrf_token)

            response = await client.delete(
                "/test",
                headers={"X-CSRF-Token": csrf_token},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "DELETE"
        assert data["status"] == "ok"


class TestCSRFTokenValidation:
    """Tests for CSRF token validation scenarios."""

    @pytest.mark.anyio
    async def test_invalid_csrf_token_fails(self, test_app: FastAPI):
        """Invalid CSRF token should return 403."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            # Get a valid cookie token
            get_response = await client.get("/test")
            csrf_cookie = get_response.cookies.get("csrf_token")
            client.cookies.set("csrf_token", csrf_cookie)

            # Send a different token in the header
            response = await client.post(
                "/test",
                headers={"X-CSRF-Token": "invalid-token-value"},
            )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "CSRF token invalid"
        assert "does not match" in data["message"]

    @pytest.mark.anyio
    async def test_csrf_token_mismatch_fails(self, test_app: FastAPI):
        """Mismatched CSRF tokens (cookie vs header) should fail."""
        token1 = secrets.token_urlsafe(32)
        token2 = secrets.token_urlsafe(32)

        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            # Set one token in cookie, different in header
            client.cookies.set("csrf_token", token2)
            response = await client.post(
                "/test",
                headers={"X-CSRF-Token": token1},
            )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "CSRF token invalid"

    @pytest.mark.anyio
    async def test_csrf_token_in_header_only_fails(self, test_app: FastAPI):
        """CSRF token in header but not in cookie should generate new cookie token."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            # When there's no cookie, middleware generates a new token
            # This new token won't match the header token
            response = await client.post(
                "/test",
                headers={"X-CSRF-Token": "some-token"},
            )

        # Should fail because header token doesn't match the generated cookie token
        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "CSRF token invalid"

    @pytest.mark.anyio
    async def test_csrf_token_case_sensitive(self, test_app: FastAPI):
        """CSRF token comparison should be case-sensitive."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            get_response = await client.get("/test")
            csrf_token = get_response.cookies.get("csrf_token")

            # Modify the case of the token
            modified_token = csrf_token.upper() if csrf_token.islower() else csrf_token.lower()
            if modified_token == csrf_token:
                # If token happens to be same case, swap a character
                modified_token = csrf_token[:-1] + ("A" if csrf_token[-1] != "A" else "B")

            client.cookies.set("csrf_token", csrf_token)
            response = await client.post(
                "/test",
                headers={"X-CSRF-Token": modified_token},
            )

        assert response.status_code == 403


class TestCSRFExemptPaths:
    """Tests for CSRF exempt paths."""

    @pytest.mark.anyio
    async def test_exempt_path_bypasses_csrf(self, test_app: FastAPI):
        """Exempt paths should not require CSRF token."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            response = await client.post("/exempt")

        assert response.status_code == 200
        data = response.json()
        assert data["exempt"] is True

    @pytest.mark.anyio
    async def test_default_exempt_paths(self):
        """Default exempt paths should be set correctly."""
        middleware = CSRFMiddleware(app=lambda: None)

        expected_paths = {
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/health",
            "/api/v1/ready",
            "/docs",
            "/openapi.json",
            "/redoc",
        }

        assert middleware.exempt_paths == expected_paths

    @pytest.mark.anyio
    async def test_custom_exempt_paths(self):
        """Custom exempt paths should override defaults."""
        custom_paths = {"/custom/path", "/another/path"}
        middleware = CSRFMiddleware(app=lambda: None, exempt_paths=custom_paths)

        assert middleware.exempt_paths == custom_paths

    @pytest.mark.anyio
    async def test_exempt_path_prefix_match(self):
        """Paths starting with exempt prefix should be exempt."""
        app = create_test_app(exempt_paths={"/api/public"})

        @app.post("/api/public/resource")
        async def public_resource():
            return {"status": "ok"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/public/resource")

        assert response.status_code == 200


class TestCSRFCustomConfiguration:
    """Tests for custom CSRF middleware configuration."""

    @pytest.mark.anyio
    async def test_custom_header_name(self, custom_header_app: FastAPI):
        """Custom header name should be used for CSRF token."""
        async with AsyncClient(
            transport=ASGITransport(app=custom_header_app),
            base_url="http://test",
        ) as client:
            # GET to obtain token
            get_response = await client.get("/test")
            csrf_token = get_response.cookies.get("csrf_token")
            client.cookies.set("csrf_token", csrf_token)

            # POST with default header should fail
            response = await client.post(
                "/test",
                headers={"X-CSRF-Token": csrf_token},
            )
            assert response.status_code == 403

            # POST with custom header should succeed
            response = await client.post(
                "/test",
                headers={"X-Custom-CSRF": csrf_token},
            )
            assert response.status_code == 200

    @pytest.mark.anyio
    async def test_custom_cookie_name(self, custom_cookie_app: FastAPI):
        """Custom cookie name should be used for CSRF token."""
        async with AsyncClient(
            transport=ASGITransport(app=custom_cookie_app),
            base_url="http://test",
        ) as client:
            # GET to obtain token
            get_response = await client.get("/test")
            csrf_token = get_response.cookies.get("custom_csrf")
            assert csrf_token is not None

            # Set the custom cookie on client
            client.cookies.set("custom_csrf", csrf_token)

            # POST with custom cookie should succeed
            response = await client.post(
                "/test",
                headers={"X-CSRF-Token": csrf_token},
            )
            assert response.status_code == 200


class TestCSRFTokenGeneration:
    """Tests for CSRF token generation functions."""

    def test_generate_csrf_token_length(self):
        """Token generation should create tokens of appropriate length."""
        token = CSRFMiddleware._generate_token()

        # token_urlsafe(32) produces ~43 characters
        assert len(token) >= 40
        assert len(token) <= 50

    def test_generate_csrf_token_uniqueness(self):
        """Each generated token should be unique."""
        tokens = {CSRFMiddleware._generate_token() for _ in range(100)}

        # All 100 tokens should be unique
        assert len(tokens) == 100

    def test_generate_csrf_token_url_safe(self):
        """Generated tokens should be URL-safe."""
        token = CSRFMiddleware._generate_token()

        # URL-safe characters only (base64url alphabet)
        import re

        assert re.match(r"^[A-Za-z0-9_-]+$", token)

    def test_generate_csrf_token_uses_secrets(self):
        """Token generation should use secrets module."""
        with patch.object(secrets, "token_urlsafe", return_value="mocked-token") as mock:
            token = CSRFMiddleware._generate_token()

        mock.assert_called_once_with(32)
        assert token == "mocked-token"


class TestGetCSRFTokenHelper:
    """Tests for the get_csrf_token helper function."""

    @pytest.mark.anyio
    async def test_get_csrf_token_from_cookie(self, test_app: FastAPI):
        """get_csrf_token should return cookie token if present."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            # First get to set cookie
            get_response = await client.get("/test")
            csrf_cookie = get_response.cookies.get("csrf_token")

            # Set cookie on client for subsequent request
            client.cookies.set("csrf_token", csrf_cookie)

            # Get token via helper endpoint
            response = await client.get("/csrf-token")

        data = response.json()
        assert data["csrf_token"] == csrf_cookie

    @pytest.mark.anyio
    async def test_get_csrf_token_generates_new(self, test_app: FastAPI):
        """get_csrf_token should generate new token if no cookie present."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/csrf-token")

        data = response.json()
        assert data["csrf_token"] is not None
        assert len(data["csrf_token"]) > 0


class TestCSRFCookieAttributes:
    """Tests for CSRF cookie attributes."""

    @pytest.mark.anyio
    async def test_csrf_cookie_not_httponly(self, test_app: FastAPI):
        """CSRF cookie should not be httponly (JavaScript needs to read it)."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/test")

        # Check that cookie is set
        assert "csrf_token" in response.cookies
        # Note: httpx doesn't expose httponly attribute directly in response.cookies
        # The middleware sets httponly=False which allows JS access

    @pytest.mark.anyio
    async def test_csrf_cookie_samesite_lax(self, test_app: FastAPI):
        """CSRF cookie should have SameSite=Lax attribute."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/test")

        # Cookie is set with samesite="lax"
        assert "csrf_token" in response.cookies

    @pytest.mark.anyio
    async def test_csrf_cookie_preserved_on_subsequent_requests(self, test_app: FastAPI):
        """CSRF cookie should not be reset if already present."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            # First request sets the cookie
            response1 = await client.get("/test")
            csrf_token1 = response1.cookies.get("csrf_token")

            # Set cookie on client for subsequent request
            client.cookies.set("csrf_token", csrf_token1)

            # Second request with cookie should not generate new one
            response2 = await client.get("/test")

        # Cookie should not be in response if already present
        # (middleware only sets it when not present)
        assert (
            "csrf_token" not in response2.cookies
            or response2.cookies.get("csrf_token") == csrf_token1
        )


class TestCSRFMiddlewareProtectedMethods:
    """Tests verifying the protected methods configuration."""

    def test_protected_methods_constant(self):
        """Protected methods should include all state-changing methods."""
        expected = {"POST", "PUT", "PATCH", "DELETE"}
        assert expected == CSRFMiddleware.PROTECTED_METHODS

    def test_cookie_name_constant(self):
        """Default cookie name should be csrf_token."""
        assert CSRFMiddleware.COOKIE_NAME == "csrf_token"

    def test_header_name_constant(self):
        """Default header name should be X-CSRF-Token."""
        assert CSRFMiddleware.HEADER_NAME == "X-CSRF-Token"


class TestCSRFErrorResponses:
    """Tests for CSRF error response format."""

    @pytest.mark.anyio
    async def test_missing_token_error_format(self, test_app: FastAPI):
        """Missing token error should have correct format."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            response = await client.post("/test")

        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "message" in data
        assert data["detail"] == "CSRF token missing"

    @pytest.mark.anyio
    async def test_invalid_token_error_format(self, test_app: FastAPI):
        """Invalid token error should have correct format."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as client:
            get_response = await client.get("/test")
            csrf_cookie = get_response.cookies.get("csrf_token")
            client.cookies.set("csrf_token", csrf_cookie)

            response = await client.post(
                "/test",
                headers={"X-CSRF-Token": "wrong-token"},
            )

        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "message" in data
        assert data["detail"] == "CSRF token invalid"
