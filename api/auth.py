"""Platform identity: parses the SWA/App Service Easy Auth headers.

Azure Static Web Apps' built-in Entra ID (AAD) auth authenticates the caller
at the edge and forwards identity to this backend via the base64-encoded JSON
``x-ms-client-principal`` header ({"identityProvider", "userId", "userDetails",
"userRoles", "claims"} -- claims may be absent). App Service Easy Auth (used
when the API itself sits behind Easy Auth rather than only the SWA) instead
sets the plain ``x-ms-client-principal-name`` / ``x-ms-client-principal-id``
headers; those are used as a fallback when the base64 header is absent.

Local dev and the test suite send neither header, so `parse_client_principal`
returns None rather than raising -- callers stay unauthenticated, matching
current behavior. A malformed header (bad base64 / bad JSON) is treated the
same as "no identity" rather than a 500: the platform is the only thing that
should ever set this header, so a decode failure means something upstream is
misconfigured, not that the request should error out.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

# The Entra object id claim -- stable across UPN/email renames -- preferred
# over SWA's own userId when both are available.
_OID_CLAIM = "http://schemas.microsoft.com/identity/claims/objectidentifier"


class CurrentUser(BaseModel):
    """The platform-authenticated caller, resolved from request headers."""

    id: str
    upn: str | None = None
    email: str | None = None
    name: str | None = None
    provider: str | None = None
    roles: list[str] = []


def _header(headers: Any, name: str) -> str | None:
    """Case-insensitive header lookup that also works with a plain dict.

    Starlette's Headers is already case-insensitive; the manual scan below
    only matters for tests that pass a plain dict fixture.
    """
    value = headers.get(name)
    if value is not None:
        return value
    lname = name.lower()
    items = getattr(headers, "items", None)
    if items is not None:
        for key, val in items():
            if key.lower() == lname:
                return val
    return None


def _claim_map(claims: Any) -> dict[str, str]:
    out: dict[str, str] = {}
    if not isinstance(claims, list):
        return out
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        typ, val = claim.get("typ"), claim.get("val")
        if typ and val is not None:
            out.setdefault(typ, val)
    return out


def _from_principal(payload: dict[str, Any]) -> CurrentUser | None:
    claims = _claim_map(payload.get("claims"))
    user_id = claims.get("oid") or claims.get(_OID_CLAIM) or payload.get("userId")
    if not user_id:
        return None
    user_details = payload.get("userDetails")
    upn = (
        user_details
        or claims.get("preferred_username")
        or claims.get("upn")
        or claims.get("email")
    )
    email = claims.get("email") or (upn if upn and "@" in upn else None)
    name = claims.get("name") or user_details
    roles = payload.get("userRoles")
    return CurrentUser(
        id=str(user_id),
        upn=upn,
        email=email,
        name=name,
        provider=payload.get("identityProvider"),
        roles=list(roles) if isinstance(roles, list) else [],
    )


def parse_client_principal(headers: Any) -> CurrentUser | None:
    """Resolve the caller from SWA/Easy Auth identity headers, or None."""
    encoded = _header(headers, "x-ms-client-principal")
    if encoded:
        try:
            payload = json.loads(base64.b64decode(encoded))
        except (ValueError, TypeError, binascii.Error, UnicodeDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        return _from_principal(payload)

    # App Service Easy Auth fallback headers (no base64 principal available).
    name_header = _header(headers, "x-ms-client-principal-name")
    id_header = _header(headers, "x-ms-client-principal-id")
    if name_header or id_header:
        return CurrentUser(
            id=id_header or name_header,
            upn=name_header,
            email=name_header if name_header and "@" in name_header else None,
            name=name_header,
        )
    return None


def get_current_user(request: Request) -> CurrentUser | None:
    """Optional-auth dependency: the caller, or None when unauthenticated."""
    return parse_client_principal(request.headers)


def require_user(user: CurrentUser | None = Depends(get_current_user)) -> CurrentUser:
    """Required-auth dependency: 401s when no identity header is present."""
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required (no x-ms-client-principal header).",
        )
    return user
