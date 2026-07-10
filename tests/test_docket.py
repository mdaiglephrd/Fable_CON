from common.docket import DocketMatch, extract_dockets, normalize_docket


def canon(raw: str) -> str | None:
    dm = normalize_docket(raw)
    return dm.canonical if dm else None


class TestNormalizeCon:
    def test_plain_forms(self):
        assert canon("CON1234567") == "CON-1234567"
        assert canon("CON-1234567") == "CON-1234567"
        assert canon("con 1234567") == "CON-1234567"
        assert canon("CON_1234567") == "CON-1234567"
        assert canon("CON.1234567") == "CON-1234567"

    def test_leading_zeros_preserved(self):
        assert canon("CON-0034567") == "CON-0034567"

    def test_label_noise(self):
        assert canon("Docket No. CON-1234567") == "CON-1234567"
        assert canon("Project # CON1234567") == "CON-1234567"
        assert canon("CON-1234567.") == "CON-1234567"

    def test_multi_group_tail(self):
        assert canon("CON 2004-021") == "CON-2004-021"

    def test_variants_include_compact_and_raw(self):
        dm = normalize_docket("con 1234567")
        assert dm is not None
        assert "CON1234567" in dm.variants
        assert "CON-1234567" in dm.variants
        assert "con 1234567" in dm.variants


class TestLegacyGa:
    def test_ga_maps_to_con(self):
        dm = normalize_docket("GA-1234567")
        assert dm is not None
        assert dm.canonical == "CON-1234567"
        assert dm.kind == "CON"
        assert "GA-1234567" in dm.variants

    def test_ga_embedded_in_filename(self):
        found = extract_dockets("Final Order GA_1234567 (signed).pdf")
        assert [d.canonical for d in found] == ["CON-1234567"]

    def test_ga_state_zip_not_matched(self):
        assert extract_dockets("Atlanta, GA 30303") == []
        assert extract_dockets("Savannah GA 31401-2210") == []


class TestDetLnr:
    def test_det(self):
        assert canon("DET2020-014") == "DET-2020-014"
        assert canon("DET-123") == "DET-123"
        dm = normalize_docket("DET2020-014")
        assert dm.kind == "DET"

    def test_lnr(self):
        assert canon("LNR-2023-008") == "LNR-2023-008"
        assert normalize_docket("LNR-2023-008").kind == "LNR"


class TestCountyLegacy:
    def test_simple(self):
        dm = normalize_docket("FULTON-213")
        assert dm.canonical == "FULTON-213"
        assert dm.kind == "COUNTY"

    def test_multi_word_county(self):
        assert canon("Ben Hill-45") == "BEN-HILL-45"
        assert canon("BEN-HILL-45") == "BEN-HILL-45"

    def test_space_separator_allowed_in_normalize_only(self):
        assert canon("Fulton 213") == "FULTON-213"
        assert extract_dockets("the Fulton 213 area") == []

    def test_longest_county_wins(self):
        assert canon("CLAYTON-5") == "CLAYTON-5"

    def test_embedded_con_not_matched_inside_county_word(self):
        found = extract_dockets("MACON-123 correspondence")
        assert [d.canonical for d in found] == ["MACON-123"]
        assert found[0].kind == "COUNTY"

    def test_non_county_word_not_matched(self):
        assert canon("SPRINGFIELD-213") is None

    def test_zip_length_number_rejected(self):
        # county number capped at 4 digits, so ZIP-like strings don't match
        assert extract_dockets("Houston-77002 facility") == []


class TestExtract:
    def test_multiple_in_order(self):
        text = "Appeal of CON-1234567; see also DET 2019-003 and FULTON-213."
        assert [d.canonical for d in extract_dockets(text)] == [
            "CON-1234567",
            "DET-2019-003",
            "FULTON-213",
        ]

    def test_dedupe_merges_variants(self):
        found = extract_dockets("CON-1234567 aka CON1234567")
        assert len(found) == 1
        assert "CON-1234567" in found[0].variants
        assert "CON1234567" in found[0].variants

    def test_empty_and_no_match(self):
        assert extract_dockets("") == []
        assert extract_dockets("quarterly budget memo") == []


class TestNormalizeRejects:
    def test_garbage(self):
        assert normalize_docket("hello world") is None
        assert normalize_docket("") is None
        assert normalize_docket("   ") is None
        assert normalize_docket("Fulton County Hospital") is None

    def test_two_dockets_is_ambiguous(self):
        assert normalize_docket("CON-1234567 and CON-7654321") is None

    def test_short_digit_run_rejected(self):
        assert normalize_docket("CON 21") is None


class TestDataclass:
    def test_frozen_and_fields(self):
        dm = normalize_docket("CON-1234567")
        assert isinstance(dm, DocketMatch)
        assert dm.raw == "CON-1234567"
