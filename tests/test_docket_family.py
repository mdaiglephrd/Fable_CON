from common import vocab
from common.docket_family import classify_family


def test_returns_only_valid_families():
    samples = [
        "CON-2026006", "DET-2020-014", "DET-EQT2024-073", "DET-ASC2026001",
        "LNR-ASC2026002", "LNR-EQT2026009", "FULTON-213", "GA-1234567",
    ]
    for s in samples:
        assert classify_family(s) in vocab.DOCKET_FAMILIES


def test_con_forms():
    assert classify_family("CON-1234567") == "CON"
    assert classify_family("CON2026006") == "CON"
    assert classify_family("con-2026-002") == "CON"


def test_county_and_ga_legacy_map_to_con():
    assert classify_family("FULTON-213") == "CON"
    assert classify_family("Ben Hill 45") == "CON"
    assert classify_family("GA-1234567") == "CON"  # GA legacy folds into CON


def test_plain_det():
    assert classify_family("DET-2020-014") == "DET"
    assert classify_family("DET2020014") == "DET"


def test_det_subtypes_by_subtype():
    assert classify_family("DET-EQT2024-073") == "DET-EQT"
    assert classify_family("DET-EQT-2024-073") == "DET-EQT"
    assert classify_family("DETEQT2024073") == "DET-EQT"
    assert classify_family("DET-ASC2026001") == "DET-ASC"
    assert classify_family("DET-ASC-2026-001") == "DET-ASC"


def test_lnr_subtypes_by_prefix():
    assert classify_family("LNR-ASC2026002") == "LNR-ASC"
    assert classify_family("LNR-ASC-2026-002") == "LNR-ASC"
    assert classify_family("LNR-EQT2026009") == "LNR-EQT"
    assert classify_family("LNR-EQT-2026-009") == "LNR-EQT"


def test_bare_lnr_falls_to_det():
    # No plain 'LNR' family exists; a bare Letter of Non-Reviewability is the
    # generic determination family.
    assert classify_family("LNR-2023-008") == "DET"


def test_empty_defaults_to_con():
    assert classify_family("") == "CON"
    assert classify_family("   ") == "CON"


def test_not_confused_by_prose_prefixes():
    # A word starting with DET/LNR but not a docket must not classify as DET.
    assert classify_family("DETROIT MEDICAL CENTER") == "CON"
