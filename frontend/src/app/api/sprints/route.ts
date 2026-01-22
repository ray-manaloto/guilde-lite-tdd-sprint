import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";
import type { SprintCreate, SprintWithItems } from "@/types";
import type { PaginatedResponse } from "@/types/api";

const getAuthHeader = (request: NextRequest): Record<string, string> => {
  const accessToken = request.cookies.get("access_token")?.value;
  if (accessToken) {
    return { Authorization: `Bearer ${accessToken}` };
  }
  return {};
};

export async function GET(request: NextRequest) {
  try {
    const params = Object.fromEntries(request.nextUrl.searchParams.entries());
    const data = await backendFetch<PaginatedResponse<SprintWithItems>>("/api/v1/sprints", {
      method: "GET",
      headers: getAuthHeader(request),
      params,
    });
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail = (error.data as { detail?: string })?.detail || "Failed to load sprints";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as SprintCreate;
    const data = await backendFetch<SprintWithItems>("/api/v1/sprints", {
      method: "POST",
      headers: getAuthHeader(request),
      body: JSON.stringify(body),
    });
    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail = (error.data as { detail?: string })?.detail || "Failed to create sprint";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
