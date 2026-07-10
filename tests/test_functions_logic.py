"""Unit tests for functions/processing.py (the Functions app's shared logic).

No Functions runtime, no live DB, no live storage: DB via tests.fakes
.FakeConnection, storage via tiny stub container clients, and the ingest
modules replaced by stubs through processing's ``_index_diff`` /
``_report_parser`` hooks — only their DESIGN.md signatures are relied on.

processing.py lives in functions/ (the Functions app root, not a package),
so it is loaded by file path under a unique module name.
"""

import importlib.util
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.fakes import FakeConnection

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_processing():
    spec = importlib.util.spec_from_file_location(
        "functions_processing", REPO_ROOT / "functions" / "processing.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


processing = _load_processing()


# --- storage fakes ---


class FakeDownloader:
    def __init__(self, data: bytes):
        self._data = data

    def readinto(self, stream) -> int:
        stream.write(self._data)
        return len(self._data)


class FakeContainerClient:
    def __init__(self, container_name: str, blobs: dict[str, bytes] | None = None):
        self.container_name = container_name
        self.blobs = dict(blobs or {})
        self.downloads: list[str] = []

    def list_blobs(self):
        return [SimpleNamespace(name=name) for name in self.blobs]

    def download_blob(self, blob_name: str) -> FakeDownloader:
        self.downloads.append(blob_name)
        return FakeDownloader(self.blobs[blob_name])


class FakeServiceClient:
    def __init__(self, *containers: FakeContainerClient):
        self._by_name = {c.container_name: c for c in containers}

    def get_container_client(self, name: str) -> FakeContainerClient:
        return self._by_name[name]


# --- ingest stubs (DESIGN.md signatures only) ---


def stub_index_diff(monkeypatch, *, records=(), diff=None, apply_error=None):
    """Install a stub ingest.index_diff; returns a dict recording the calls."""
    calls: dict = {"read_paths": []}

    def read_snapshot(path):
        calls["read_paths"].append(str(path))
        return iter(list(records))

    def diff_snapshots(old_iter, new_iter):
        list(old_iter)
        list(new_iter)
        calls["diffed"] = True
        return diff

    def apply_diff(conn, d, old_blob_name, new_blob_name):
        if apply_error is not None:
            raise apply_error
        calls["applied"] = (old_blob_name, new_blob_name)
        assert d is diff

    stub = SimpleNamespace(
        read_snapshot=read_snapshot, diff_snapshots=diff_snapshots, apply_diff=apply_diff
    )
    monkeypatch.setattr(processing, "_index_diff", lambda: stub)
    return calls


def stub_report_parser(monkeypatch, *, parse, stats="LoadStats(inserted=2, skipped=0)"):
    calls: dict = {}

    def extract_text(pdf_path):
        calls["pdf_path"] = str(pdf_path)
        return "PAGE ONE\fPAGE TWO"

    def parse_report_text(text, report_file=""):
        calls["parsed"] = (text, report_file)
        return parse

    def load_events(conn, p, report_file):
        calls["loaded"] = (p, report_file)
        return stats

    stub = SimpleNamespace(
        extract_text=extract_text, parse_report_text=parse_report_text, load_events=load_events
    )
    monkeypatch.setattr(processing, "_report_parser", lambda: stub)
    return calls


def merge_calls(conn: FakeConnection) -> list[tuple]:
    return [params for sql, params in conn.executed if "MERGE con.processed_blob" in sql]


# --- helpers ---


class TestHelpers:
    def test_blob_key_is_container_slash_name(self):
        assert processing.blob_key("index-snapshots", "a.jsonl.gz") == "index-snapshots/a.jsonl.gz"

    def test_split_blob_path(self):
        assert processing.split_blob_path("weekly-reports/sub/r.pdf") == (
            "weekly-reports",
            "sub/r.pdf",
        )
        with pytest.raises(ValueError):
            processing.split_blob_path("no-slash")

    def test_snapshot_date_from_name(self):
        assert processing.snapshot_date_from_name("index-2026-07-04.jsonl.gz") == date(2026, 7, 4)
        assert processing.snapshot_date_from_name("index_20260704.jsonl.gz") == date(2026, 7, 4)
        assert processing.snapshot_date_from_name("snapshot.jsonl.gz") is None
        assert processing.snapshot_date_from_name("index-2026-99-99.jsonl.gz") is None


# --- snapshot processing ---


class TestProcessSnapshotBlob:
    def test_already_succeeded_blob_is_skipped(self, monkeypatch):
        conn = FakeConnection()
        conn.script("SELECT status FROM con.processed_blob", rows=[("succeeded",)])
        container = FakeContainerClient("index-snapshots", {"snap.jsonl.gz": b"gz"})
        stub_index_diff(monkeypatch)

        result = processing.process_snapshot_blob(conn, container, "snap.jsonl.gz")

        assert "skipped" in result
        assert container.downloads == []
        assert merge_calls(conn) == []
        assert conn.committed == 0

    def test_non_snapshot_suffix_is_ignored(self, monkeypatch):
        conn = FakeConnection()
        container = FakeContainerClient("index-snapshots", {"notes.txt": b"x"})
        stub_index_diff(monkeypatch)

        result = processing.process_snapshot_blob(conn, container, "notes.txt")

        assert "ignored" in result
        assert conn.executed == []

    def test_baseline_registers_snapshot_and_processed_blob(self, monkeypatch):
        conn = FakeConnection()  # no scripts: not processed, no prior snapshot
        container = FakeContainerClient("index-snapshots", {"index-2026-07-04.jsonl.gz": b"gz"})
        calls = stub_index_diff(monkeypatch, records=[{"id": 5}, {"id": 12}, {"id": 9}])

        detail = processing.process_snapshot_blob(conn, container, "index-2026-07-04.jsonl.gz")

        assert "baseline" in detail
        assert container.downloads == ["index-2026-07-04.jsonl.gz"]
        assert calls["read_paths"][0].endswith(".jsonl.gz")
        insert = next(p for s, p in conn.executed if "INSERT INTO con.index_snapshot" in s)
        assert insert == ("index-2026-07-04.jsonl.gz", date(2026, 7, 4), 3, 12)
        (merge,) = merge_calls(conn)
        assert merge[0] == "index-snapshots/index-2026-07-04.jsonl.gz"
        assert merge[1] == "succeeded"
        assert conn.committed == 1
        assert conn.rolled_back == 0

    def test_diff_path_downloads_both_and_applies(self, monkeypatch):
        conn = FakeConnection()
        conn.script(
            "FROM con.index_snapshot ORDER BY snapshot_id DESC",
            rows=[(7, "old.jsonl.gz")],
            columns=["snapshot_id", "blob_name"],
        )
        container = FakeContainerClient(
            "index-snapshots", {"old.jsonl.gz": b"old", "new.jsonl.gz": b"new"}
        )
        diff = SimpleNamespace(added=[{}, {}], modified=[({}, {})], deleted=[])
        calls = stub_index_diff(monkeypatch, diff=diff)

        detail = processing.process_snapshot_blob(conn, container, "new.jsonl.gz")

        assert calls["applied"] == ("old.jsonl.gz", "new.jsonl.gz")
        assert sorted(container.downloads) == ["new.jsonl.gz", "old.jsonl.gz"]
        assert "added=2" in detail and "modified=1" in detail and "deleted=0" in detail
        (merge,) = merge_calls(conn)
        assert merge[1] == "succeeded"
        # No baseline INSERT on the diff path (apply_diff owns snapshot registration).
        assert not any("INSERT INTO con.index_snapshot" in s for s in conn.executed_sql())
        assert conn.committed == 1

    def test_same_blob_as_latest_snapshot_records_without_diff(self, monkeypatch):
        conn = FakeConnection()
        conn.script("FROM con.index_snapshot ORDER BY snapshot_id DESC", rows=[(3, "snap.jsonl.gz")])
        container = FakeContainerClient("index-snapshots", {"snap.jsonl.gz": b"gz"})
        calls = stub_index_diff(monkeypatch)

        detail = processing.process_snapshot_blob(conn, container, "snap.jsonl.gz")

        assert "already registered" in detail
        assert container.downloads == []
        assert "diffed" not in calls
        (merge,) = merge_calls(conn)
        assert merge[1] == "succeeded"

    def test_failure_records_failed_and_reraises(self, monkeypatch):
        conn = FakeConnection()
        conn.script("FROM con.index_snapshot ORDER BY snapshot_id DESC", rows=[(7, "old.jsonl.gz")])
        container = FakeContainerClient(
            "index-snapshots", {"old.jsonl.gz": b"old", "new.jsonl.gz": b"new"}
        )
        diff = SimpleNamespace(added=[], modified=[], deleted=[])
        stub_index_diff(monkeypatch, diff=diff, apply_error=RuntimeError("boom"))

        with pytest.raises(RuntimeError, match="boom"):
            processing.process_snapshot_blob(conn, container, "new.jsonl.gz")

        (merge,) = merge_calls(conn)
        assert merge[0] == "index-snapshots/new.jsonl.gz"
        assert merge[1] == "failed"
        assert "RuntimeError" in merge[2] and "boom" in merge[2]
        assert conn.rolled_back == 1  # partial work rolled back before the failure record
        assert conn.committed == 1  # the failure record itself is committed

    def test_previously_failed_blob_is_retried(self, monkeypatch):
        conn = FakeConnection()
        conn.script("SELECT status FROM con.processed_blob", rows=[("failed",)])
        container = FakeContainerClient("index-snapshots", {"snap.jsonl.gz": b"gz"})
        stub_index_diff(monkeypatch, records=[{"id": 1}])

        detail = processing.process_snapshot_blob(conn, container, "snap.jsonl.gz")

        assert "baseline" in detail
        (merge,) = merge_calls(conn)
        assert merge[1] == "succeeded"


# --- report processing ---


class TestProcessReportBlob:
    def test_report_is_parsed_and_loaded(self, monkeypatch):
        conn = FakeConnection()
        container = FakeContainerClient("weekly-reports", {"report.pdf": b"%PDF-fake"})
        parse = SimpleNamespace(report_date=date(2026, 7, 2), events=[1, 2, 3], warnings=["w"])
        calls = stub_report_parser(monkeypatch, parse=parse)

        detail = processing.process_report_blob(conn, container, "report.pdf")

        assert calls["pdf_path"].endswith(".pdf")
        assert calls["parsed"] == ("PAGE ONE\fPAGE TWO", "report.pdf")
        assert calls["loaded"] == (parse, "report.pdf")
        assert "events=3" in detail and "warnings=1" in detail
        assert "report_date=2026-07-02" in detail
        (merge,) = merge_calls(conn)
        assert merge[0] == "weekly-reports/report.pdf"
        assert merge[1] == "succeeded"
        assert conn.committed == 1

    def test_already_succeeded_report_is_skipped(self, monkeypatch):
        conn = FakeConnection()
        conn.script("SELECT status FROM con.processed_blob", rows=[("succeeded",)])
        container = FakeContainerClient("weekly-reports", {"report.pdf": b"%PDF-fake"})
        stub_report_parser(monkeypatch, parse=SimpleNamespace())

        result = processing.process_report_blob(conn, container, "report.pdf")

        assert "skipped" in result
        assert container.downloads == []
        assert merge_calls(conn) == []

    def test_parse_failure_records_failed_and_reraises(self, monkeypatch):
        conn = FakeConnection()
        container = FakeContainerClient("weekly-reports", {"report.pdf": b"%PDF-fake"})

        def extract_text(pdf_path):
            raise ValueError("not a pdf")

        stub = SimpleNamespace(extract_text=extract_text)
        monkeypatch.setattr(processing, "_report_parser", lambda: stub)

        with pytest.raises(ValueError, match="not a pdf"):
            processing.process_report_blob(conn, container, "report.pdf")

        (merge,) = merge_calls(conn)
        assert merge[1] == "failed"
        assert "ValueError" in merge[2] and "not a pdf" in merge[2]
        assert conn.rolled_back == 1


# --- catch-up sweep ---


class TestSweepContainers:
    @pytest.fixture(autouse=True)
    def _containers_env(self, monkeypatch):
        monkeypatch.setenv("SNAPSHOT_CONTAINER", "index-snapshots")
        monkeypatch.setenv("REPORT_CONTAINER", "weekly-reports")

    def test_sweep_picks_only_unprocessed_blobs(self, monkeypatch):
        conn = FakeConnection()
        conn.script(
            "WHERE status = 'succeeded'",
            rows=[("index-snapshots/a.jsonl.gz",)],
            columns=["blob_name"],
        )
        snapshots = FakeContainerClient(
            "index-snapshots", {"a.jsonl.gz": b"", "b.jsonl.gz": b""}
        )
        reports = FakeContainerClient("weekly-reports", {"r.pdf": b""})
        service = FakeServiceClient(snapshots, reports)

        seen: list[tuple[str, str]] = []
        monkeypatch.setattr(
            processing,
            "process_snapshot_blob",
            lambda conn, cc, name: seen.append((cc.container_name, name)) or "ok",
        )
        monkeypatch.setattr(
            processing,
            "process_report_blob",
            lambda conn, cc, name: seen.append((cc.container_name, name)) or "ok",
        )

        counts = processing.sweep_containers(conn, service)

        assert ("index-snapshots", "b.jsonl.gz") in seen
        assert ("weekly-reports", "r.pdf") in seen
        assert ("index-snapshots", "a.jsonl.gz") not in seen
        assert counts == {"processed": 2, "failed": 0, "skipped": 1}

    def test_sweep_continues_past_a_failing_blob(self, monkeypatch):
        conn = FakeConnection()
        snapshots = FakeContainerClient("index-snapshots", {"bad.jsonl.gz": b""})
        reports = FakeContainerClient("weekly-reports", {"r.pdf": b""})
        service = FakeServiceClient(snapshots, reports)

        def boom(conn, cc, name):
            raise RuntimeError("poison")

        processed: list[str] = []
        monkeypatch.setattr(processing, "process_snapshot_blob", boom)
        monkeypatch.setattr(
            processing,
            "process_report_blob",
            lambda conn, cc, name: processed.append(name) or "ok",
        )

        counts = processing.sweep_containers(conn, service)

        assert processed == ["r.pdf"]
        assert counts == {"processed": 1, "failed": 1, "skipped": 0}
