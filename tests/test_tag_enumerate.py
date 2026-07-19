import os

from ingest.tag_enumerate import enumerate_candidate_files


def test_enumerates_files_recursively(tmp_path):
    (tmp_path / "CON2005029").mkdir()
    (tmp_path / "CON2005029" / "a.pdf").write_bytes(b"a")
    (tmp_path / "CON2005029" / "sub").mkdir()
    (tmp_path / "CON2005029" / "sub" / "b.pdf").write_bytes(b"bb")

    found = {str(c.path.relative_to(tmp_path)) for c in enumerate_candidate_files(tmp_path)}
    assert found == {
        os.path.join("CON2005029", "a.pdf"),
        os.path.join("CON2005029", "sub", "b.pdf"),
    }


def test_skips_directories(tmp_path):
    (tmp_path / "a_dir").mkdir()
    (tmp_path / "a_dir" / "inner.pdf").write_bytes(b"x")

    found = [c.path for c in enumerate_candidate_files(tmp_path)]
    assert all(p.is_file() for p in found)
    assert (tmp_path / "a_dir") not in found


def test_yields_size_and_timestamps(tmp_path):
    path = tmp_path / "file.pdf"
    path.write_bytes(b"hello world")

    [candidate] = list(enumerate_candidate_files(tmp_path))
    assert candidate.size_bytes == 11
    assert candidate.modified_at > 0
    assert candidate.created_at > 0


def test_empty_directory_yields_nothing(tmp_path):
    assert list(enumerate_candidate_files(tmp_path)) == []


def test_excludes_state_architect_files_subtree(tmp_path):
    docket = tmp_path / "CON2005029"
    (docket / "8 State Architect Files" / "nested").mkdir(parents=True)
    (docket / "8 State Architect Files" / "site_plan.pdf").write_bytes(b"x")
    (docket / "8 State Architect Files" / "nested" / "inspection.pdf").write_bytes(b"y")
    (docket / "1 Master File").mkdir()
    (docket / "1 Master File" / "kept.pdf").write_bytes(b"z")

    found = {c.path.name for c in enumerate_candidate_files(tmp_path)}
    assert found == {"kept.pdf"}


def test_excludes_state_architect_files_case_and_prefix_insensitive(tmp_path):
    docket = tmp_path / "CON2005029"
    (docket / "state architect files").mkdir(parents=True)
    (docket / "state architect files" / "drawing.pdf").write_bytes(b"x")

    assert list(enumerate_candidate_files(tmp_path)) == []


def test_only_pdfs_are_enumerated(tmp_path):
    docket = tmp_path / "CON2020003" / "1 Initial Hearing Officer Appeal"
    docket.mkdir(parents=True)
    (docket / "kept.pdf").write_bytes(b"x")
    (docket / "deposition.mp4").write_bytes(b"y")
    (docket / "notes.docx").write_bytes(b"z")
    (docket / "scan.jpg").write_bytes(b"w")
    (docket / "email.msg").write_bytes(b"v")
    # Different base name (not the same name in a different case) -- on
    # case-insensitive filesystems (Windows/NTFS), "kept.pdf" and "KEPT.PDF"
    # are the same file, so writing both would silently overwrite one with
    # the other rather than testing anything.
    (docket / "OTHER.PDF").write_bytes(b"u")  # case-insensitive extension match

    found = {c.path.name for c in enumerate_candidate_files(tmp_path)}
    assert found == {"kept.pdf", "OTHER.PDF"}


def test_continues_past_unreadable_entry(tmp_path, monkeypatch):
    good = tmp_path / "good.pdf"
    bad = tmp_path / "bad.pdf"
    good.write_bytes(b"ok")
    bad.write_bytes(b"also ok")

    real_stat = os.stat

    def flaky_stat(path, *args, **kwargs):
        if str(path).endswith("bad.pdf"):
            raise OSError("permission denied")
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr("ingest.tag_enumerate.os.stat", flaky_stat)

    found = {c.path.name for c in enumerate_candidate_files(tmp_path)}
    assert found == {"good.pdf"}
