from pathlib import Path

import openpyxl
import pytest

from ingest.tag_crosswalk import (
    CrosswalkIndex,
    IndexRow,
    infer_doc_type_phase,
    load_index,
    resolve_entry_id,
)

CON_PATH = (
    r"Regulatory Compliance\2005 Forward\1 Certificate of Need\2005"
    r"\CON2005029 Saint Marys Health Care System Inc\1 Master File"
    r"\1 Review Files\A Main Application\CON2005029 Main Application"
)
CON_APPENDIX_A = (
    r"Regulatory Compliance\2005 Forward\1 Certificate of Need\2005"
    r"\CON2005029 Saint Marys Health Care System Inc\1 Master File"
    r"\1 Review Files\B Appendices\CON2005029 Appendix A"
)
CON_APPENDIX_B = (
    r"Regulatory Compliance\2005 Forward\1 Certificate of Need\2005"
    r"\CON2005029 Saint Marys Health Care System Inc\1 Master File"
    r"\1 Review Files\B Appendices\CON2005029 Appendix B"
)
LNR_ASC_PATH = (
    r"Regulatory Compliance\2005 Forward\3 Letters of Non-Reviewability"
    r"\1 Ambulatory Surgery\2005\LNR-ASC2005006 Gastroenterology Specialists of Gwinnett"
    r"\1 LNR File\1 Evaluation\LNR-ASC2005006 Request"
)


def _index(rows: list[IndexRow]) -> CrosswalkIndex:
    return CrosswalkIndex(rows)


# --- load_index ---------------------------------------------------------------


def test_load_index_reads_xlsx(tmp_path):
    path = tmp_path / "index.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Path", "Name", "Type", "Entry ID", "Page Count"])
    ws.append([CON_PATH, "CON2005029 Main Application", "document", 1043, 57])
    ws.append([CON_APPENDIX_A, "CON2005029 Appendix A", "document", 1044, 3])
    wb.save(path)

    index = load_index(path)
    assert len(index) == 2
    rows = index.candidates_for_docket("CON-2005029")
    assert {r.entry_id for r in rows} == {1043, 1044}


def test_load_index_skips_rows_without_entry_id(tmp_path):
    path = tmp_path / "index.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Path", "Name", "Type", "Entry ID", "Page Count"])
    ws.append([CON_PATH, "CON2005029 Main Application", "document", None, 57])
    wb.save(path)

    index = load_index(path)
    assert len(index) == 0


# --- infer_doc_type_phase -------------------------------------------------------


@pytest.mark.parametrize(
    "parts,expected",
    [
        (("...", "A Main Application", "file"), ("Application/Request", "Initial Application")),
        (("...", "B Appendices", "file"), ("Application/Request", "Initial Application")),
        (("...", "G Letters of Opposition", "file"), ("Correspondence", "Initial Application")),
        (("...", "J Decision", "file"), ("Decision/Determination", "Initial Application")),
        (
            ("...", "1 Initial Hearing Officer Appeal", "file"),
            ("Hearing Officer Decision", "Administrative Appeal"),
        ),
        (("...", "3 Judicial Review", "file"), ("Court Order/Opinion", "Judicial Review – Superior Court")),
        (("...", "1 Determination File", "file"), ("Decision/Determination", "Initial Application")),
    ],
)
def test_infer_doc_type_phase_known_folders(parts, expected):
    assert infer_doc_type_phase(parts) == expected


def test_infer_doc_type_phase_unknown_folder_returns_none():
    assert infer_doc_type_phase(("...", "Some Unmapped Folder", "file")) == (None, None)


def test_infer_doc_type_phase_too_short_path():
    assert infer_doc_type_phase(("file",)) == (None, None)


# --- resolve_entry_id ------------------------------------------------------------


def test_resolve_entry_id_exact_match():
    index = _index(
        [
            IndexRow(path=CON_PATH, name="CON2005029 Main Application", entry_id=1043, page_count=57),
            IndexRow(path=CON_APPENDIX_A, name="CON2005029 Appendix A", entry_id=1044, page_count=3),
        ]
    )
    result = resolve_entry_id(Path("CON2005029/1 Master File/A Main Application/CON2005029 Main Application"), index)
    assert result.entry_id == 1043
    assert result.docket_id == "CON-2005029"
    assert not result.unresolved


def test_resolve_entry_id_no_docket_in_path_is_unresolved():
    index = _index([IndexRow(path=CON_PATH, name="CON2005029 Main Application", entry_id=1043, page_count=57)])
    result = resolve_entry_id(Path("misc/randomly_named_file"), index)
    assert result.unresolved
    assert result.entry_id is None
    assert result.docket_id is None


def test_resolve_entry_id_docket_not_in_index_is_unresolved():
    index = _index([IndexRow(path=CON_PATH, name="CON2005029 Main Application", entry_id=1043, page_count=57)])
    result = resolve_entry_id(Path("CON9999999/Some File"), index)
    assert result.unresolved
    assert result.docket_id == "CON-9999999"


def test_resolve_entry_id_ambiguous_near_tie_is_unresolved():
    # Two candidates in the same docket with near-identical names/scores.
    index = _index(
        [
            IndexRow(path=CON_APPENDIX_A, name="CON2005029 Appendix A", entry_id=1044, page_count=3),
            IndexRow(path=CON_APPENDIX_B, name="CON2005029 Appendix A", entry_id=1045, page_count=3),
        ]
    )
    result = resolve_entry_id(Path("CON2005029/B Appendices/CON2005029 Appendix A"), index)
    assert result.unresolved
    assert len(result.candidates) == 2


def test_resolve_entry_id_page_count_breaks_near_tie():
    index = _index(
        [
            IndexRow(path=CON_APPENDIX_A, name="CON2005029 Appendix A", entry_id=1044, page_count=3),
            IndexRow(path=CON_APPENDIX_B, name="CON2005029 Appendix B", entry_id=1045, page_count=83),
        ]
    )
    # Without the page-count cross-check this is a near-tie (both candidates
    # are equally similar to the query stem); the actual page count (83)
    # should decisively pick entry 1045.
    result = resolve_entry_id(
        Path("CON2005029/B Appendices/CON2005029 Appendix"),
        index,
        actual_page_count=83,
    )
    assert result.entry_id == 1045


def test_resolve_entry_id_low_similarity_is_unresolved():
    index = _index([IndexRow(path=CON_PATH, name="Completely Different Title Zzz", entry_id=1043, page_count=57)])
    result = resolve_entry_id(Path("CON2005029/xk9"), index)
    assert result.unresolved


def test_resolve_entry_id_handles_lnr_asc_docket():
    index = _index(
        [IndexRow(path=LNR_ASC_PATH, name="LNR-ASC2005006 Request", entry_id=5000, page_count=2)]
    )
    result = resolve_entry_id(
        Path("LNR-ASC2005006/1 Evaluation/LNR-ASC2005006 Request"), index
    )
    assert result.entry_id == 5000
    assert result.docket_id == "LNR-ASC-2005006"


def test_shared_docket_prefix_does_not_inflate_similarity():
    # "DET2005018 Notes" and "DET2005018 Determin Request" share only the
    # docket id; a file that is NOT in the index must not fuzzy-match onto an
    # unrelated document purely on that shared prefix.
    det_path = (
        r"Regulatory Compliance\2005 Forward\2 Determinations\2005"
        r"\DET2005018 Diagnostic Systems of Georgia LLC\1 Determination File"
        r"\1 Evaluation\DET2005018 Determin Request"
    )
    index = _index(
        [IndexRow(path=det_path, name="DET2005018 Determin Request", entry_id=5018, page_count=1)]
    )
    result = resolve_entry_id(Path("DET2005018/1 Evaluation/DET2005018 Notes.txt"), index)
    assert result.unresolved


def test_file_named_exactly_the_docket_id_still_matches():
    # Stripping the docket id leaves nothing on the file side -- scoring must
    # fall back to the unstripped strings rather than failing on empty input.
    index = _index(
        [IndexRow(path=CON_PATH, name="CON2005029", entry_id=1043, page_count=1)]
    )
    result = resolve_entry_id(Path("CON2005029/A Main Application/CON2005029"), index)
    assert result.entry_id == 1043
