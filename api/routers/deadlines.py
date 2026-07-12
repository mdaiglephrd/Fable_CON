"""POST /deadlines/calculate — regulatory deadlines from a trigger event.

Pure passthrough to common.deadline_rules.compute_deadlines (the single
source of truth shared with the con.deadline_rule seed). No DB access.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, field_validator

from common import vocab
from common.deadline_rules import compute_deadlines

router = APIRouter()


class DeadlineCalcRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    family: str
    trigger_event: str = Field(alias="triggerEvent", min_length=1)
    date: date

    @field_validator("family")
    @classmethod
    def _known_family(cls, value: str) -> str:
        if value not in vocab.DOCKET_FAMILIES:
            raise ValueError(
                f"Unknown docket family {value!r}; one of: {', '.join(vocab.DOCKET_FAMILIES)}"
            )
        return value


@router.post("/deadlines/calculate")
def calculate_deadlines(request: DeadlineCalcRequest) -> dict[str, Any]:
    deadlines = compute_deadlines(request.family, request.trigger_event, request.date)
    return {
        "family": request.family,
        "triggerEvent": request.trigger_event,
        "date": request.date,
        "deadlines": [
            {
                "label": deadline.label,
                "dueDate": deadline.due_date,
                "basisStatute": deadline.basis_statute,
                "description": deadline.description,
            }
            for deadline in deadlines
        ],
    }
