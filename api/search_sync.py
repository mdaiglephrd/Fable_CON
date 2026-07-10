"""Sync Azure SQL rows into the Azure AI Search index `con-records`.

CLI:
    python -m api.search_sync [--recreate] [--skip-vectors] [--batch-size 200]

Creates/updates the index definition, then streams matters (with aggregated
child values), documents (denormalized with their matter's fields), and weekly
report events, shaping each row into a search document whose `content` field is
a readable concatenation of the record's fields. Vectors are computed via
api.search_client.embed unless --skip-vectors is passed or Azure OpenAI is not
configured (then the vector field is omitted; the index still defines it).

The row -> search-doc shaping functions are pure and unit-testable.
"""

import argparse
import sys
from collections.abc import Iterable, Iterator
from datetime import date, datetime
from typing import Any

from api import search_client

VECTOR_DIMENSIONS = 1536
VECTOR_PROFILE = "con-vector-profile"
VECTOR_ALGORITHM = "con-hnsw"
SEMANTIC_CONFIGURATION = "con-semantic"

MULTI_VALUE_SEPARATOR = ";"

# ---------------------------------------------------------------------------
# Pure shaping helpers (no Azure, no DB)
# ---------------------------------------------------------------------------


def _split_multi(value: Any) -> list[str]:
    """Split an aggregated child-value string ('a;b') into a clean list."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v]
    return [part.strip() for part in str(value).split(MULTI_VALUE_SEPARATOR) if part.strip()]


def _iso_date(value: Any) -> str | None:
    """Render a date-ish value as an Azure Search DateTimeOffset string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, date):
        return f"{value.isoformat()}T00:00:00Z"
    return str(value)


def _compose_content(pairs: list[tuple[str, Any]]) -> str:
    """Readable 'Label: value' concatenation of a record's populated fields."""
    lines: list[str] = []
    for label, value in pairs:
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, (list, tuple)):
            value = ", ".join(str(v) for v in value)
        lines.append(f"{label}: {value}")
    return "\n".join(lines)


def matter_to_search_doc(row: dict[str, Any]) -> dict[str, Any]:
    """Shape a con.matter row (with aggregated service_types/phases) for search."""
    service_types = _split_multi(row.get("service_types"))
    phases = _split_multi(row.get("phases"))
    title_bits = [row.get("docket_id"), row.get("applicant") or row.get("facility")]
    content = _compose_content(
        [
            ("Docket", row.get("docket_id")),
            ("Matter type", row.get("matter_type")),
            ("Action type", row.get("action_type")),
            ("Applicant", row.get("applicant")),
            ("Facility", row.get("facility")),
            ("County", row.get("county")),
            ("Service area", row.get("service_area")),
            ("Service types", service_types),
            ("Phases", phases),
            ("Bed count", row.get("bed_count")),
            ("Year filed", row.get("year_filed")),
            ("Final outcome", row.get("final_outcome")),
            ("Final decision date", row.get("final_decision_date")),
        ]
    )
    return {
        "key": f"matter_{row['docket_id']}",
        "record_type": "matter",
        "docket_id": row.get("docket_id"),
        "entry_id": None,
        "title": " — ".join(str(b) for b in title_bits if b),
        "content": content,
        "applicant": row.get("applicant"),
        "facility": row.get("facility"),
        "county": row.get("county"),
        "service_types": service_types,
        "matter_type": row.get("matter_type"),
        "action_type": row.get("action_type"),
        "doc_type": None,
        "phase": None,
        "outcome": row.get("final_outcome"),
        "year_filed": row.get("year_filed"),
        "doc_date": _iso_date(row.get("final_decision_date")),
        "validation_status": None,
        "docview_url": None,
    }


def document_to_search_doc(row: dict[str, Any]) -> dict[str, Any]:
    """Shape a con.document row (joined with its matter's fields) for search."""
    service_types = _split_multi(row.get("service_types"))
    title_bits = [row.get("file_name") or f"Entry {row.get('entry_id')}", row.get("docket_id")]
    content = _compose_content(
        [
            ("Document", row.get("file_name")),
            ("Docket", row.get("docket_id")),
            ("Document type", row.get("doc_type")),
            ("Phase", row.get("phase")),
            ("Decision maker", row.get("decision_maker")),
            ("Outcome", row.get("outcome")),
            ("Document date", row.get("doc_date")),
            ("Applicant", row.get("applicant")),
            ("Facility", row.get("facility")),
            ("County", row.get("county")),
            ("Service types", service_types),
            ("Matter type", row.get("matter_type")),
            ("Action type", row.get("action_type")),
            ("Template", row.get("template_name")),
            ("Source path", row.get("source_path")),
            ("Validation status", row.get("validation_status")),
        ]
    )
    return {
        "key": f"document_{row['entry_id']}",
        "record_type": "document",
        "docket_id": row.get("docket_id"),
        "entry_id": row.get("entry_id"),
        "title": " — ".join(str(b) for b in title_bits if b),
        "content": content,
        "applicant": row.get("applicant"),
        "facility": row.get("facility"),
        "county": row.get("county"),
        "service_types": service_types,
        "matter_type": row.get("matter_type"),
        "action_type": row.get("action_type"),
        "doc_type": row.get("doc_type"),
        "phase": row.get("phase"),
        "outcome": row.get("outcome"),
        "year_filed": row.get("year_filed"),
        "doc_date": _iso_date(row.get("doc_date")),
        "validation_status": row.get("validation_status"),
        "docview_url": row.get("docview_url"),
    }


def event_to_search_doc(row: dict[str, Any]) -> dict[str, Any]:
    """Shape a con.weekly_report_event row for search."""
    title_bits = [
        row.get("section"),
        row.get("docket_id") or row.get("docket_raw"),
        row.get("applicant"),
    ]
    content = _compose_content(
        [
            ("Weekly report section", row.get("section")),
            ("Report date", row.get("report_date")),
            ("Docket", row.get("docket_id") or row.get("docket_raw")),
            ("Applicant", row.get("applicant")),
            ("Project description", row.get("project_description")),
            ("County", row.get("county")),
            ("Cost", row.get("cost")),
            ("Opposition", row.get("opposition")),
            ("Filing date", row.get("filing_date")),
            ("Decision deadline", row.get("decision_deadline")),
            ("Decision date", row.get("decision_date")),
        ]
    )
    return {
        "key": f"event_{row['event_id']}",
        "record_type": "event",
        "docket_id": row.get("docket_id"),
        "entry_id": None,
        "title": " — ".join(str(b) for b in title_bits if b),
        "content": content,
        "applicant": row.get("applicant"),
        "facility": None,
        "county": row.get("county"),
        "service_types": [],
        "matter_type": None,
        "action_type": None,
        "doc_type": None,
        "phase": None,
        "outcome": None,
        "year_filed": None,
        "doc_date": _iso_date(row.get("report_date")),
        "validation_status": None,
        "docview_url": None,
    }


def batched(docs: Iterable[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    batch: list[dict[str, Any]] = []
    for doc in docs:
        batch.append(doc)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


# ---------------------------------------------------------------------------
# Index definition
# ---------------------------------------------------------------------------


def build_index(name: str) -> Any:
    """The con-records SearchIndex definition (idempotent create_or_update)."""
    from azure.search.documents.indexes.models import (
        HnswAlgorithmConfiguration,
        SearchField,
        SearchFieldDataType,
        SearchableField,
        SemanticConfiguration,
        SemanticField,
        SemanticPrioritizedFields,
        SemanticSearch,
        SimpleField,
        VectorSearch,
        VectorSearchProfile,
    )

    def facet(field_name: str, data_type: Any = SearchFieldDataType.String) -> SimpleField:
        return SimpleField(name=field_name, type=data_type, filterable=True, facetable=True)

    fields = [
        SimpleField(name="key", type=SearchFieldDataType.String, key=True),
        facet("record_type"),
        SimpleField(name="docket_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="entry_id", type=SearchFieldDataType.Int64, filterable=True),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchableField(name="applicant", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="facility", type=SearchFieldDataType.String, filterable=True),
        facet("county"),
        SearchField(
            name="service_types",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            facetable=True,
            searchable=False,
        ),
        facet("matter_type"),
        facet("action_type"),
        facet("doc_type"),
        facet("phase"),
        facet("outcome"),
        facet("year_filed", SearchFieldDataType.Int32),
        SimpleField(
            name="doc_date",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
        facet("validation_status"),
        SimpleField(name="docview_url", type=SearchFieldDataType.String),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=VECTOR_DIMENSIONS,
            vector_search_profile_name=VECTOR_PROFILE,
        ),
    ]
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name=VECTOR_ALGORITHM)],
        profiles=[
            VectorSearchProfile(
                name=VECTOR_PROFILE, algorithm_configuration_name=VECTOR_ALGORITHM
            )
        ],
    )
    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name=SEMANTIC_CONFIGURATION,
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="title"),
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[
                        SemanticField(field_name="applicant"),
                        SemanticField(field_name="facility"),
                    ],
                ),
            )
        ]
    )
    from azure.search.documents.indexes.models import SearchIndex

    return SearchIndex(
        name=name, fields=fields, vector_search=vector_search, semantic_search=semantic_search
    )


# ---------------------------------------------------------------------------
# SQL streaming
# ---------------------------------------------------------------------------

_MATTER_SQL = """
SELECT m.docket_id, m.applicant, m.facility, m.matter_type, m.action_type, m.county,
       m.service_area, m.bed_count, m.year_filed, m.final_outcome, m.final_decision_date,
       m.highest_review_level,
       (SELECT STRING_AGG(st.service_type, ';')
          FROM con.matter_service_type st WHERE st.docket_id = m.docket_id) AS service_types,
       (SELECT STRING_AGG(mp.phase, ';')
          FROM con.matter_phase mp WHERE mp.docket_id = m.docket_id) AS phases
FROM con.matter m
"""

_DOCUMENT_SQL = """
SELECT d.entry_id, d.docket_id, d.docview_url, d.file_name, d.doc_type, d.decision_level,
       d.phase, d.doc_date, d.decision_maker, d.outcome, d.template_name, d.source_path,
       d.validation_status,
       m.applicant, m.facility, m.county, m.matter_type, m.action_type, m.year_filed,
       (SELECT STRING_AGG(st.service_type, ';')
          FROM con.matter_service_type st WHERE st.docket_id = d.docket_id) AS service_types
FROM con.document d
LEFT JOIN con.matter m ON m.docket_id = d.docket_id
"""

_EVENT_SQL = """
SELECT e.event_id, e.report_date, e.section, e.docket_id, e.docket_raw, e.applicant,
       e.project_description, e.county, e.cost, e.opposition, e.filing_date,
       e.decision_deadline, e.decision_date
FROM con.weekly_report_event e
"""


def _iter_dict_rows(conn: Any, sql: str) -> Iterator[dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute(sql)
    columns = [col[0] for col in cursor.description or []]
    for row in cursor:
        yield dict(zip(columns, row))


def iter_search_docs(conn: Any) -> Iterator[dict[str, Any]]:
    for row in _iter_dict_rows(conn, _MATTER_SQL):
        yield matter_to_search_doc(row)
    for row in _iter_dict_rows(conn, _DOCUMENT_SQL):
        yield document_to_search_doc(row)
    for row in _iter_dict_rows(conn, _EVENT_SQL):
        yield event_to_search_doc(row)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _attach_vectors(batch: list[dict[str, Any]]) -> None:
    vectors = search_client.embed([doc["content"] or doc["title"] or "" for doc in batch])
    for doc, vector in zip(batch, vectors):
        doc["content_vector"] = vector


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m api.search_sync",
        description="Create/update the con-records AI Search index and push SQL rows.",
    )
    parser.add_argument("--recreate", action="store_true", help="delete and rebuild the index")
    parser.add_argument(
        "--skip-vectors", action="store_true", help="do not compute content_vector embeddings"
    )
    parser.add_argument("--batch-size", type=int, default=200)
    args = parser.parse_args(argv)

    index_name = search_client.search_index_name()
    index_client = search_client.get_search_index_client()
    if args.recreate:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            index_client.delete_index(index_name)
            print(f"deleted index {index_name}")
        except ResourceNotFoundError:
            pass
    index_client.create_or_update_index(build_index(index_name))
    print(f"index {index_name} created/updated")

    use_vectors = not args.skip_vectors and search_client.openai_configured()
    if not use_vectors:
        reason = "--skip-vectors" if args.skip_vectors else "Azure OpenAI not configured"
        print(f"vectors omitted ({reason})")

    from common.db import get_connection  # lazy: pyodbc needs system ODBC libraries

    client = search_client.get_search_client()
    conn = get_connection()
    uploaded = 0
    try:
        for batch in batched(iter_search_docs(conn), max(1, args.batch_size)):
            if use_vectors:
                _attach_vectors(batch)
            client.merge_or_upload_documents(batch)
            uploaded += len(batch)
            print(f"uploaded {uploaded} documents", end="\r", flush=True)
    finally:
        conn.close()
    print(f"\ndone: {uploaded} documents synced to {index_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
