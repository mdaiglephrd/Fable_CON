"""Azure AI Search semantic/hybrid retrieval and the grounded /ask endpoint.

GET /search/semantic — hybrid (keyword + vector) query with semantic ranking,
degrading gracefully to keyword-only when embeddings or the semantic
configuration are unavailable.

POST /ask — retrieve top-k records from AI Search, then answer with Azure
OpenAI chat, grounded ONLY in the retrieved records, with per-claim citations.

ConfigurationError raised here is converted to HTTP 503 by api.main.
"""

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api import search_client
from api.search_client import ConfigurationError

logger = logging.getLogger(__name__)

router = APIRouter()

SEMANTIC_CONFIGURATION = "con-semantic"
VECTOR_FIELD = "content_vector"
DEFAULT_ASK_K = 8
SNIPPET_CHARS = 300

_RESULT_FIELDS = (
    "key",
    "record_type",
    "docket_id",
    "entry_id",
    "title",
    "applicant",
    "facility",
    "county",
    "doc_type",
    "outcome",
    "validation_status",
    "docview_url",
)


def _snippet(content: Any) -> str | None:
    if not content:
        return None
    text = " ".join(str(content).split())
    return text[:SNIPPET_CHARS] + ("…" if len(text) > SNIPPET_CHARS else "")


def _vector_queries(q: str, k: int) -> tuple[list[Any], str | None]:
    """Build a vector query for hybrid search; None + reason when unavailable."""
    if not search_client.openai_configured():
        return [], "embeddings not configured (AZURE_OPENAI_ENDPOINT unset)"
    try:
        vector = search_client.embed([q])[0]
    except ConfigurationError as exc:
        return [], str(exc)
    except Exception as exc:  # embedding is an enrichment; never fail the search
        logger.warning("embedding failed; falling back to keyword-only: %s", exc)
        return [], f"embedding failed: {exc}"
    from azure.search.documents.models import VectorizedQuery

    return (
        [VectorizedQuery(vector=vector, k_nearest_neighbors=k, fields=VECTOR_FIELD)],
        None,
    )


def _retrieve(q: str, k: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Top-k records from AI Search. Returns (hits, mode metadata).

    Raises ConfigurationError when SEARCH_ENDPOINT is not configured.
    """
    from azure.core.exceptions import HttpResponseError

    client = search_client.get_search_client()
    vectors, degraded_reason = _vector_queries(q, k)
    kwargs: dict[str, Any] = {"search_text": q, "top": k}
    if vectors:
        kwargs["vector_queries"] = vectors
    mode = {
        "hybrid": bool(vectors),
        "semantic_ranking": True,
        "degraded_reason": degraded_reason,
    }
    try:
        results = client.search(
            query_type="semantic",
            semantic_configuration_name=SEMANTIC_CONFIGURATION,
            **kwargs,
        )
        raw = list(results)
    except HttpResponseError as exc:
        # Semantic configuration unavailable (e.g. free tier) — keyword/vector only.
        logger.warning("semantic query failed; retrying without semantic ranking: %s", exc)
        mode["semantic_ranking"] = False
        mode["degraded_reason"] = degraded_reason or f"semantic ranking unavailable: {exc}"
        raw = list(client.search(**kwargs))

    hits: list[dict[str, Any]] = []
    for doc in raw:
        hit = {field: doc.get(field) for field in _RESULT_FIELDS}
        hit["snippet"] = _snippet(doc.get("content"))
        hit["score"] = doc.get("@search.score")
        hit["reranker_score"] = doc.get("@search.reranker_score")
        hits.append(hit)
    return hits, mode


@router.get("/search/semantic")
def semantic_search(q: str, k: int = 10) -> dict[str, Any]:
    k = max(1, min(k, 50))
    hits, mode = _retrieve(q, k)
    return {"query": q, "k": k, "mode": mode, "results": hits}


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    k: int = DEFAULT_ASK_K


_SYSTEM_PROMPT = (
    "You are a research assistant for the Georgia DCH Certificate of Need (CON) "
    "database. Answer the user's question using ONLY the numbered records provided; "
    "never use outside knowledge. Cite every claim with the record's identifier in "
    "square brackets, e.g. [CON-1234567] or [entry 12345] — use the entry_id when "
    "the record is a document, otherwise the docket_id. If a cited record's "
    "validation_status is anything other than 'Validated', explicitly flag it as "
    "unvalidated (e.g. 'unvalidated record'). If the records do not contain the "
    "answer, say so plainly instead of guessing."
)


def _record_block(index: int, hit: dict[str, Any]) -> str:
    lines = [f"[{index}] key={hit.get('key')}"]
    for field in (
        "record_type",
        "docket_id",
        "entry_id",
        "title",
        "applicant",
        "facility",
        "county",
        "doc_type",
        "outcome",
        "validation_status",
        "docview_url",
    ):
        value = hit.get(field)
        if value not in (None, ""):
            lines.append(f"  {field}: {value}")
    if hit.get("snippet"):
        lines.append(f"  content: {hit['snippet']}")
    return "\n".join(lines)


def _grounded_prompt(question: str, hits: list[dict[str, Any]]) -> str:
    blocks = "\n\n".join(_record_block(i + 1, hit) for i, hit in enumerate(hits))
    return f"Question: {question}\n\nRecords:\n\n{blocks}"


def _citations(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "key": hit.get("key"),
            "docket_id": hit.get("docket_id"),
            "entry_id": hit.get("entry_id"),
            "docview_url": hit.get("docview_url"),
            "snippet": hit.get("snippet"),
            "validation_status": hit.get("validation_status"),
        }
        for hit in hits
    ]


@router.post("/ask")
def ask(request: AskRequest) -> dict[str, Any]:
    k = max(1, min(request.k, 50))
    hits, _mode = _retrieve(request.question, k)
    if not hits:
        return {
            "answer": (
                "No matching records were found in the CON search index for this "
                "question, so no grounded answer can be given."
            ),
            "citations": [],
        }
    client = search_client.get_openai_client()
    response = client.chat.completions.create(
        model=search_client.chat_deployment(),
        temperature=0,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _grounded_prompt(request.question, hits)},
        ],
    )
    answer = response.choices[0].message.content or ""
    return {"answer": answer, "citations": _citations(hits)}
