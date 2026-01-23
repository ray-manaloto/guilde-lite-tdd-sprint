# ADR-001 Implementation: Pagination Fix

## API Contract Status

**No API Contract Changes Required**

The fix maintains the existing API contract:

```yaml
# OpenAPI Specification (unchanged)
GET /api/v1/sprints/{sprint_id}/items:
  parameters:
    - name: sprint_id
      in: path
      required: true
      schema:
        type: string
        format: uuid
    - name: page
      in: query
      required: false
      schema:
        type: integer
        default: 1
    - name: size
      in: query
      required: false
      schema:
        type: integer
        default: 50
  responses:
    200:
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Page_SprintItemRead_'
    404:
      description: Sprint not found
```

The `Page[SprintItemRead]` response model remains identical:

```json
{
  "items": [
    {
      "id": "uuid",
      "sprint_id": "uuid",
      "title": "string",
      "description": "string|null",
      "status": "todo|in_progress|done",
      "priority": "integer",
      "estimate_points": "integer|null",
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ],
  "total": 0,
  "page": 1,
  "size": 50,
  "pages": 0
}
```

## Implementation Code

### Before (Broken)

```python
# /backend/app/api/routes/v1/sprints.py lines 95-102

from fastapi_pagination.ext.sqlalchemy import paginate

@router.get("/{sprint_id}/items", response_model=Page[SprintItemRead])
async def list_sprint_items(
    sprint_id: UUID,
    sprint_service: SprintSvc,
):
    """List sprint items for a sprint."""
    items = await sprint_service.list_items(sprint_id)
    return paginate(items)  # BUG: paginate expects (db, query), not list
```

### After (Fixed)

```python
# /backend/app/api/routes/v1/sprints.py lines 95-108

from sqlalchemy import select
from fastapi_pagination.ext.sqlalchemy import paginate

from app.db.models.sprint import SprintItem  # Add this import at top

@router.get("/{sprint_id}/items", response_model=Page[SprintItemRead])
async def list_sprint_items(
    sprint_id: UUID,
    db: DBSession,
    sprint_service: SprintSvc,
):
    """List sprint items for a sprint."""
    # Verify sprint exists (raises NotFoundError if not)
    await sprint_service.get_by_id(sprint_id)

    # Build query for pagination at route level
    query = (
        select(SprintItem)
        .where(SprintItem.sprint_id == sprint_id)
        .order_by(SprintItem.created_at.desc())
    )
    return await paginate(db, query)
```

## Testing the Fix

### Manual Testing

```bash
# Create a sprint first
curl -X POST http://localhost:8000/api/v1/sprints \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Sprint", "goal": "Test pagination"}'

# Note the sprint_id from response, then:

# Create some items
curl -X POST http://localhost:8000/api/v1/sprints/{sprint_id}/items \
  -H "Content-Type: application/json" \
  -d '{"title": "Item 1", "status": "todo", "priority": 1}'

curl -X POST http://localhost:8000/api/v1/sprints/{sprint_id}/items \
  -H "Content-Type: application/json" \
  -d '{"title": "Item 2", "status": "todo", "priority": 2}'

# Test pagination (this was broken, should now work)
curl "http://localhost:8000/api/v1/sprints/{sprint_id}/items?page=1&size=10"

# Expected response format:
# {
#   "items": [...],
#   "total": 2,
#   "page": 1,
#   "size": 10,
#   "pages": 1
# }
```

### Automated Test

```python
# /backend/tests/test_sprint_items_pagination.py

import pytest
from httpx import AsyncClient
from uuid import UUID

@pytest.mark.asyncio
async def test_list_sprint_items_pagination(client: AsyncClient, db_session):
    """Test that sprint items endpoint returns paginated response."""
    # Create sprint
    response = await client.post(
        "/api/v1/sprints",
        json={"name": "Test Sprint", "goal": "Test pagination"}
    )
    assert response.status_code == 201
    sprint_id = response.json()["id"]

    # Create multiple items
    for i in range(15):
        await client.post(
            f"/api/v1/sprints/{sprint_id}/items",
            json={"title": f"Item {i}", "status": "todo", "priority": i}
        )

    # Test pagination - page 1
    response = await client.get(
        f"/api/v1/sprints/{sprint_id}/items",
        params={"page": 1, "size": 10}
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 10
    assert data["total"] == 15
    assert data["page"] == 1
    assert data["size"] == 10
    assert data["pages"] == 2

    # Test pagination - page 2
    response = await client.get(
        f"/api/v1/sprints/{sprint_id}/items",
        params={"page": 2, "size": 10}
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 5
    assert data["page"] == 2


@pytest.mark.asyncio
async def test_list_sprint_items_nonexistent_sprint(client: AsyncClient):
    """Test that listing items for nonexistent sprint returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/v1/sprints/{fake_id}/items")
    assert response.status_code == 404
```

## Diff Summary

```diff
--- a/backend/app/api/routes/v1/sprints.py
+++ b/backend/app/api/routes/v1/sprints.py
@@ -8,6 +8,7 @@ from fastapi_pagination.ext.sqlalchemy import paginate
 from sqlalchemy import select

 from app.api.deps import DBSession, SprintSvc
-from app.db.models.sprint import Sprint, SprintStatus
+from app.db.models.sprint import Sprint, SprintItem, SprintStatus
 from app.schemas.sprint import (
     SprintCreate,
@@ -95,9 +96,17 @@ async def delete_sprint(
 @router.get("/{sprint_id}/items", response_model=Page[SprintItemRead])
 async def list_sprint_items(
     sprint_id: UUID,
+    db: DBSession,
     sprint_service: SprintSvc,
 ):
     """List sprint items for a sprint."""
-    items = await sprint_service.list_items(sprint_id)
-    return paginate(items)
+    # Verify sprint exists (raises NotFoundError if not)
+    await sprint_service.get_by_id(sprint_id)
+
+    # Build query for pagination at route level
+    query = (
+        select(SprintItem)
+        .where(SprintItem.sprint_id == sprint_id)
+        .order_by(SprintItem.created_at.desc())
+    )
+    return await paginate(db, query)
```

## Rollback Plan

If issues arise, revert by:

1. Remove `SprintItem` from imports
2. Remove `db: DBSession` parameter
3. Restore original `paginate(items)` call
4. Note: The endpoint will return errors again, but this is the known-broken state

The service method `sprint_service.list_items()` remains available if we need to fall back to non-paginated response.
