---
name: gen-migration
description: Generate an Alembic migration with proper async patterns
metadata:
  claude:
    disable-model-invocation: true
    arguments:
      - name: message
        description: Migration description (e.g., "add users table")
        required: true
---

# Generate Alembic Migration

Generate a new database migration for this FastAPI project.

## Prerequisites
- Ensure the database is running and accessible
- Ensure model changes are saved in `backend/app/db/models/`

## Steps

1. **Review current models** in `backend/app/db/models/` to understand the changes being migrated

2. **Generate the migration**:
   ```bash
   cd backend && uv run alembic revision --autogenerate -m "{message}"
   ```

3. **Review the generated migration** for:
   - Correct table/column changes
   - Proper async-compatible operations
   - No unintended data-destructive operations (DROP without user confirmation)
   - Proper index and constraint naming

4. **Show the generated migration file** to the user and explain what it will do

5. **Offer to apply the migration** if the user wants:
   ```bash
   cd backend && uv run alembic upgrade head
   ```

## Common Issues

- If autogenerate produces an empty migration, ensure models are imported in `backend/app/db/models/__init__.py`
- For complex migrations (data transforms), suggest writing the migration manually
