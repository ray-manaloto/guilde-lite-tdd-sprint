/**
 * Application constants.
 */

export const APP_NAME = "guilde_lite_tdd_sprint";
export const APP_DESCRIPTION = "A FastAPI project";

// Public API URL (used for OAuth redirects in the browser)
export const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// API Routes (Next.js internal routes)
export const API_ROUTES = {
  // Auth
  LOGIN: "/auth/login",
  REGISTER: "/auth/register",
  LOGOUT: "/auth/logout",
  REFRESH: "/auth/refresh",
  ME: "/auth/me",

  // Health
  HEALTH: "/health",

  // Users
  USERS: "/users",

  // Chat (AI Agent)
  CHAT: "/chat",
  // TDD Runs
  TDD_RUNS: "/tdd-runs",
  // Sprints
  SPRINTS: "/sprints",
} as const;

// Navigation routes
export const ROUTES = {
  HOME: "/",
  LOGIN: "/login",
  REGISTER: "/register",
  DASHBOARD: "/dashboard",
  CHAT: "/chat",
  TDD: "/tdd",
  SPRINTS: "/sprints",
  KANBAN: "/kanban",
  PROFILE: "/profile",
  SETTINGS: "/settings",
} as const;

// WebSocket URL (for chat - this needs to be direct to backend for WS)
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
