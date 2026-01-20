# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
"""Spec workflow routes."""

from uuid import UUID

from fastapi import APIRouter, status
from fastapi_pagination import Page, paginate
from sqlalchemy import select

from app.api.deps import DBSession, SpecSvc
from app.db.models.spec import Spec, SpecStatus
from app.schemas.spec import (
    SpecCreate,
    SpecPlanningAnswers,
    SpecPlanningCreate,
    SpecPlanningResponse,
    SpecRead,
    SpecValidationResponse,
)

router = APIRouter()


@router.get("", response_model=Page[SpecRead])
async def list_specs(
    db: DBSession,
    status: SpecStatus | None = None,
):
    """List specs with optional status filter."""
    query = select(Spec).order_by(Spec.created_at.desc())
    if status is not None:
        query = query.where(Spec.status == status)
    return await paginate(db, query)


@router.post("", response_model=SpecRead, status_code=status.HTTP_201_CREATED)
async def create_spec(
    spec_in: SpecCreate,
    spec_service: SpecSvc,
):
    """Create a spec draft."""
    return await spec_service.create(spec_in)


@router.post("/planning", response_model=SpecPlanningResponse, status_code=status.HTTP_201_CREATED)
async def create_planning_interview(
    payload: SpecPlanningCreate,
    spec_service: SpecSvc,
):
    """Create a spec and generate planning interview questions."""
    spec, planning = await spec_service.create_with_planning(
        SpecCreate(title=payload.title, task=payload.task),
        max_questions=payload.max_questions,
    )
    return {"spec": spec, "planning": planning}


@router.get("/{spec_id}", response_model=SpecRead)
async def get_spec(
    spec_id: UUID,
    spec_service: SpecSvc,
):
    """Get a spec by ID."""
    return await spec_service.get_by_id(spec_id)


@router.post("/{spec_id}/validate", response_model=SpecValidationResponse)
async def validate_spec(
    spec_id: UUID,
    spec_service: SpecSvc,
):
    """Validate a spec and update its status."""
    spec, validation = await spec_service.validate(spec_id)
    return {"spec": spec, "validation": validation}


@router.post(
    "/{spec_id}/planning/answers",
    response_model=SpecPlanningResponse,
)
async def save_planning_answers(
    spec_id: UUID,
    payload: SpecPlanningAnswers,
    spec_service: SpecSvc,
):
    """Store planning interview answers for a spec."""
    spec, planning = await spec_service.save_planning_answers(spec_id, payload.answers)
    return {"spec": spec, "planning": planning}
