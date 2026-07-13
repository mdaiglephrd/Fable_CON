"""Pure validation for Georgia CON Tagging Taxonomy Axis 1-4 assignments.

Enforces, without a database, the same invariants schema/migrations/0011
enforces with triggers: Axis 1/2 values (when given) must be real vocabulary
codes, Axis 3/4 codes must exist in the taxonomy and not repeat, and a
document tagged Masterfile on Axis 2 must carry no Axis 3/4 tags.
ingest/load_axis_tags.py calls validate_tags() before any DB write so bad
rows land in a --rejects report instead of ever reaching the DB triggers.
"""

from __future__ import annotations

from collections.abc import Sequence

from common.axis_taxonomy import (
    AXIS1_PROCEEDING_TYPE,
    AXIS2_AUTHORITY_TYPE,
    AXIS3_BY_CODE,
    AXIS4_BY_CODE,
    MASTERFILE,
)


def validate_tags(
    axis1: str | None,
    axis2: str | None,
    axis3_codes: Sequence[str],
    axis4_codes: Sequence[str],
) -> list[str]:
    """Validate one document's Axis 1-4 assignment; return error messages (empty = valid).

    axis1/axis2 are single values; None means "not tagged on that axis" and is
    not itself an error (a document may be tagged incrementally). axis3_codes/
    axis4_codes may be empty.
    """
    errors: list[str] = []

    if axis1 is not None and axis1 not in AXIS1_PROCEEDING_TYPE:
        errors.append(f"axis1: unknown proceeding type {axis1!r}")

    if axis2 is not None and axis2 not in AXIS2_AUTHORITY_TYPE:
        errors.append(f"axis2: unknown authority type {axis2!r}")

    errors.extend(_validate_codes("axis3", axis3_codes, AXIS3_BY_CODE))
    errors.extend(_validate_codes("axis4", axis4_codes, AXIS4_BY_CODE))

    if axis2 == MASTERFILE and (axis3_codes or axis4_codes):
        errors.append(
            "masterfile: a document tagged Masterfile on Axis 2 must carry no Axis 3/4 tags"
        )

    return errors


def _validate_codes(axis_name: str, codes: Sequence[str], by_code: dict) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for code in codes:
        if code not in by_code:
            errors.append(f"{axis_name}: unknown code {code!r}")
        elif code in seen:
            errors.append(f"{axis_name}: duplicate code {code!r}")
        seen.add(code)
    return errors
