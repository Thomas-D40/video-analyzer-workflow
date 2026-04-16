"""
Unit tests for app/core/auth.py

Tests verify_api_key and verify_admin_password (called via asyncio.run).
"""
import asyncio
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials

from app.core.auth import verify_api_key, verify_admin_password


def _run(coro):
    """Helper to run async functions in sync tests."""
    return asyncio.run(coro)


def _make_settings(api_keys=None, admin_password=None):
    mock = MagicMock()
    mock.api_keys_set = set(api_keys) if api_keys else set()
    mock.admin_password = admin_password
    return mock


# ---------------------------------------------------------------------------
# verify_api_key
# ---------------------------------------------------------------------------

def test_verify_api_key_no_keys_configured():
    # When no API keys are configured → open access (returns True)
    settings = _make_settings(api_keys=[])
    with patch("app.core.auth.get_settings", return_value=settings):
        result = _run(verify_api_key(api_key=None))
    assert result is True


def test_verify_api_key_valid_key():
    settings = _make_settings(api_keys=["valid-key-123"])
    with patch("app.core.auth.get_settings", return_value=settings):
        result = _run(verify_api_key(api_key="valid-key-123"))
    assert result is True


def test_verify_api_key_invalid_key():
    settings = _make_settings(api_keys=["valid-key-123"])
    with patch("app.core.auth.get_settings", return_value=settings):
        with pytest.raises(HTTPException) as exc_info:
            _run(verify_api_key(api_key="wrong-key"))
    assert exc_info.value.status_code == 403


def test_verify_api_key_no_key_provided():
    # Keys are configured but no key is provided in the request
    settings = _make_settings(api_keys=["valid-key-123"])
    with patch("app.core.auth.get_settings", return_value=settings):
        with pytest.raises(HTTPException) as exc_info:
            _run(verify_api_key(api_key=None))
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# verify_admin_password
# ---------------------------------------------------------------------------

def test_verify_admin_no_password_configured():
    # When admin_password is not set → open access
    settings = _make_settings(admin_password=None)
    credentials = HTTPBasicCredentials(username="admin", password="anything")
    with patch("app.core.auth.get_settings", return_value=settings):
        result = _run(verify_admin_password(credentials=credentials))
    assert result is True


def test_verify_admin_valid_credentials():
    settings = _make_settings(admin_password="secret123")
    credentials = HTTPBasicCredentials(username="admin", password="secret123")
    with patch("app.core.auth.get_settings", return_value=settings):
        result = _run(verify_admin_password(credentials=credentials))
    assert result is True


def test_verify_admin_invalid_password():
    settings = _make_settings(admin_password="secret123")
    credentials = HTTPBasicCredentials(username="admin", password="wrongpass")
    with patch("app.core.auth.get_settings", return_value=settings):
        with pytest.raises(HTTPException) as exc_info:
            _run(verify_admin_password(credentials=credentials))
    assert exc_info.value.status_code == 401


def test_verify_admin_invalid_username():
    settings = _make_settings(admin_password="secret123")
    credentials = HTTPBasicCredentials(username="notadmin", password="secret123")
    with patch("app.core.auth.get_settings", return_value=settings):
        with pytest.raises(HTTPException) as exc_info:
            _run(verify_admin_password(credentials=credentials))
    assert exc_info.value.status_code == 401
