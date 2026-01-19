"""API v1 router aggregation."""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

from fastapi import APIRouter

from app.api.routes.v1 import health
from app.api.routes.v1 import auth, users
from app.api.routes.v1 import oauth
from app.api.routes.v1 import sessions
from app.api.routes.v1 import items
from app.api.routes.v1 import webhooks
from app.api.routes.v1 import ws
from app.api.routes.v1 import agent
from app.api.routes.v1 import agent_runs
from app.api.routes.v1 import tdd_runs
from app.api.routes.v1 import sprints

v1_router = APIRouter()

# Health check routes (no auth required)
v1_router.include_router(health.router, tags=["health"])

# Authentication routes
v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# User routes
v1_router.include_router(users.router, prefix="/users", tags=["users"])

# OAuth2 routes
v1_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])

# Session management routes
v1_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])

# Example CRUD routes (items)
v1_router.include_router(items.router, prefix="/items", tags=["items"])

# Webhook routes
v1_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

# WebSocket routes
v1_router.include_router(ws.router, tags=["websocket"])

# AI Agent routes
v1_router.include_router(agent.router, tags=["agent"])

# Agent run checkpointing routes
v1_router.include_router(agent_runs.router, prefix="/agent-runs", tags=["agent-runs"])

# TDD multi-subagent routes
v1_router.include_router(tdd_runs.router, prefix="/tdd-runs", tags=["tdd-runs"])

# Sprint planning routes
v1_router.include_router(sprints.router, prefix="/sprints", tags=["sprints"])
