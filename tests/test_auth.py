"""Unit tests for api/auth.py — no live DB, no TestClient (pure header parsing)."""

import base64
import json

from api.auth import CurrentUser, parse_client_principal


def _encode(payload: dict) -> str:
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


def test_parse_full_principal_with_claims_prefers_oid():
    payload = {
        "identityProvider": "aad",
        "userId": "swa-user-id-123",
        "userDetails": "matt@custerfucks.com",
        "userRoles": ["authenticated", "attorney"],
        "claims": [
            {"typ": "http://schemas.microsoft.com/identity/claims/objectidentifier",
             "val": "11111111-2222-3333-4444-555555555555"},
            {"typ": "name", "val": "Matt Custer"},
            {"typ": "preferred_username", "val": "matt@custerfucks.com"},
        ],
    }
    headers = {"x-ms-client-principal": _encode(payload)}

    user = parse_client_principal(headers)

    assert isinstance(user, CurrentUser)
    assert user.id == "11111111-2222-3333-4444-555555555555"  # oid wins over userId
    assert user.upn == "matt@custerfucks.com"
    assert user.email == "matt@custerfucks.com"
    assert user.name == "Matt Custer"
    assert user.provider == "aad"
    assert user.roles == ["authenticated", "attorney"]


def test_parse_minimal_principal_no_claims_falls_back_to_userid_and_userdetails():
    payload = {
        "identityProvider": "aad",
        "userId": "swa-user-id-456",
        "userDetails": "someone@example.com",
    }
    headers = {"x-ms-client-principal": _encode(payload)}

    user = parse_client_principal(headers)

    assert user is not None
    assert user.id == "swa-user-id-456"  # no oid claim; falls back to userId
    assert user.upn == "someone@example.com"
    assert user.email == "someone@example.com"  # userDetails looks like an email
    assert user.name == "someone@example.com"  # no name claim; falls back to userDetails
    assert user.roles == []


def test_parse_principal_missing_both_oid_and_userid_returns_none():
    payload = {"identityProvider": "aad", "userDetails": "no-id@example.com"}
    headers = {"x-ms-client-principal": _encode(payload)}

    assert parse_client_principal(headers) is None


def test_parse_garbage_base64_returns_none_not_raise():
    headers = {"x-ms-client-principal": "%%%not-base64%%%"}
    assert parse_client_principal(headers) is None


def test_parse_valid_base64_invalid_json_returns_none():
    headers = {"x-ms-client-principal": base64.b64encode(b"not json").decode("ascii")}
    assert parse_client_principal(headers) is None


def test_parse_no_headers_returns_none():
    assert parse_client_principal({}) is None


def test_parse_falls_back_to_easyauth_name_and_id_headers():
    headers = {
        "x-ms-client-principal-id": "aad-oid-789",
        "x-ms-client-principal-name": "fallback@example.com",
    }

    user = parse_client_principal(headers)

    assert user is not None
    assert user.id == "aad-oid-789"
    assert user.upn == "fallback@example.com"
    assert user.email == "fallback@example.com"
    assert user.name == "fallback@example.com"


def test_parse_easyauth_name_only_uses_name_as_id():
    headers = {"x-ms-client-principal-name": "onlyname@example.com"}
    user = parse_client_principal(headers)
    assert user is not None
    assert user.id == "onlyname@example.com"
    assert user.upn == "onlyname@example.com"


def test_parse_header_lookup_is_case_insensitive_for_plain_dicts():
    payload = {"userId": "abc", "userDetails": "case@example.com"}
    headers = {"X-MS-CLIENT-PRINCIPAL": _encode(payload)}
    user = parse_client_principal(headers)
    assert user is not None
    assert user.id == "abc"
