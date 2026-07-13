from common.axis_validation import validate_tags


def test_fully_valid_tag_set_has_no_errors():
    errors = validate_tags("CON", "Application (non-authority)", ["110", "120"], ["P110"])
    assert errors == []


def test_untagged_axes_are_not_errors():
    assert validate_tags(None, None, [], []) == []


def test_unknown_axis1_value_is_rejected():
    errors = validate_tags("NOT-A-REAL-VALUE", None, [], [])
    assert any("axis1" in e for e in errors)


def test_unknown_axis2_value_is_rejected():
    errors = validate_tags(None, "Not An Authority Type", [], [])
    assert any("axis2" in e for e in errors)


def test_unknown_axis3_code_is_rejected():
    errors = validate_tags(None, None, ["999"], [])
    assert any("axis3" in e for e in errors)


def test_unknown_axis4_code_is_rejected():
    errors = validate_tags(None, None, [], ["P999"])
    assert any("axis4" in e for e in errors)


def test_duplicate_axis3_code_is_rejected():
    errors = validate_tags(None, None, ["110", "110"], [])
    assert any("duplicate" in e and "axis3" in e for e in errors)


def test_duplicate_axis4_code_is_rejected():
    errors = validate_tags(None, None, [], ["P110", "P110"])
    assert any("duplicate" in e and "axis4" in e for e in errors)


# --- Masterfile rule -------------------------------------------------------


def test_masterfile_with_no_axis3_or_axis4_is_valid():
    assert validate_tags("CON", "Masterfile", [], []) == []


def test_masterfile_with_axis3_tags_is_rejected():
    errors = validate_tags("CON", "Masterfile", ["110"], [])
    assert any("masterfile" in e.lower() for e in errors)


def test_masterfile_with_axis4_tags_is_rejected():
    errors = validate_tags("CON", "Masterfile", [], ["P110"])
    assert any("masterfile" in e.lower() for e in errors)


def test_masterfile_with_both_axis3_and_axis4_tags_is_rejected():
    errors = validate_tags("CON", "Masterfile", ["110"], ["P110"])
    assert any("masterfile" in e.lower() for e in errors)


def test_non_masterfile_authority_type_permits_axis3_and_axis4():
    errors = validate_tags("CON", "Statute", ["110"], ["P110"])
    assert errors == []
