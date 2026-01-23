# ADR-001: Pagination Pattern for FastAPI Routes

## Status
**Proposed** (2026-01-22)

## Context

The `list_sprint_items` endpoint at `/backend/app/api/routes/v1/sprints.py:95-102` has a bug where it uses the SQLAlchemy-specific `paginate` function incorrectly:

```python
from fastapi_pagination.ext.sqlalchemy import paginate  # SQLAlchemy-only!

@router.get("/{sprint_id}/items", response_model=Page[SprintItemRead])
async def list_sprint_items(sprint_id: UUID, sprint_service: SprintSvc):
    items = await sprint_service.list_items(sprint_id)
    return paginate(items)  # ERROR: expects (db, query), not list
```

The issue is that `fastapi_pagination.ext.sqlalchemy.paginate` expects `(AsyncSession, Select)` arguments, but is being passed a `list[SprintItem]`. The service layer correctly returns a list, but the route incorrectly uses the SQLAlchemy paginator.

### Current State Analysis

1. **List Sprints** (`GET /sprints`) - CORRECT
   - Uses `paginate(db, query)` at route level
   - Bypasses service layer for pagination

2. **List Items** (`GET /items`) - CORRECT
   - Uses `paginate(db, select(Item))` at route level
   - Same pattern as List Sprints

3. **List Sprint Items** (`GET /sprints/{id}/items`) - BROKEN
   - Calls `sprint_service.list_items()` which returns `list[SprintItem]`
   - Incorrectly passes list to SQLAlchemy paginator

### Design Tension

There is an architectural tension between two patterns:

| Pattern | Pros | Cons |
|---------|------|------|
| **Route-level query pagination** | Cleaner DB integration, fastapi-pagination handles offset/limit | Routes need DB access, bypasses service layer |
| **Service returns list** | Clean service API, testable | Loses DB-level pagination, memory inefficient for large datasets |

## Decision

**Approach 2: Refactor to Query-Based Pagination (Recommended)**

Create a consistent pattern where routes needing pagination construct queries directly and use the SQLAlchemy paginator. This aligns with the existing patterns in `items.py` and the `list_sprints` endpoint.

### Implementation

1. Add `DBSession` dependency to `list_sprint_items` route
2. Build query at route level with sprint_id filter
3. Use `paginate(db, query)` consistently

```python
@router.get("/{sprint_id}/items", response_model=Page[SprintItemRead])
async def list_sprint_items(
    sprint_id: UUID,
    db: DBSession,
    sprint_service: SprintSvc,
):
    """List sprint items for a sprint."""
    # Verify sprint exists (service still owns validation)
    await sprint_service.get_by_id(sprint_id)

    # Pagination at route level (consistent with other list endpoints)
    query = (
        select(SprintItem)
        .where(SprintItem.sprint_id == sprint_id)
        .order_by(SprintItem.created_at.desc())
    )
    return await paginate(db, query)
```

### Alternatives Considered

#### Alternative 1: Dual Import with Aliases (Quick Fix)

```python
from fastapi_pagination import paginate as paginate_sequence
from fastapi_pagination.ext.sqlalchemy import paginate as paginate_query
```

**Rejected because:**
- Creates inconsistent patterns across routes
- Hides the underlying architectural tension
- Requires full dataset fetch before pagination (inefficient)

#### Alternative 2: Service Returns Query Object

```python
async def list_items_query(self, sprint_id: UUID) -> Select:
    await self.get_by_id(sprint_id)
    return select(SprintItem).where(SprintItem.sprint_id == sprint_id)
```

**Rejected because:**
- Leaks SQLAlchemy into service API
- Makes testing more complex
- Service layer should not know about pagination

#### Alternative 3: Repository Handles Pagination Parameters

```python
async def get_by_sprint_paginated(
    db, sprint_id, page: int, size: int
) -> tuple[list[SprintItem], int]:
    ...
```

**Rejected because:**
- Duplicates pagination logic
- fastapi-pagination already handles this well
- Inconsistent with existing patterns

## Consequences

### Positive
- Consistent pagination pattern across all list endpoints
- DB-level offset/limit (memory efficient)
- Service layer stays clean (business logic only)
- Existing tests continue to work

### Negative
- Routes have direct DB access for pagination queries
- Slight duplication of query logic between routes and repositories
- Need to import SprintItem model in route file

### Neutral
- Route complexity increases slightly
- Service `list_items()` method becomes unused for this endpoint (can be kept for non-paginated use cases)

## Implementation Checklist

- [ ] Update `/backend/app/api/routes/v1/sprints.py` line 95-102
- [ ] Add `from app.db.models.sprint import SprintItem` import
- [ ] Add `DBSession` dependency to route function
- [ ] Verify sprint exists via service before pagination
- [ ] Test with curl/httpie to confirm pagination works
- [ ] Update API documentation if needed

## Related Skills

The following installed skills may provide additional guidance:

- `skills/pytest-testing/` - For testing the pagination fix
- `skills/code-refactor/` - For refactoring patterns

Read with: `cat skills/<skill-name>/SKILL.md`
