import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";
import type { SprintItemCreate, SprintItem } from "@/types";
import type { PaginatedResponse } from "@/types/api";

const getAuthHeader = (request: NextRequest) => {
  const accessToken = request.cookies.get("access_token")?.value;
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
};

interface RouteParams {
  params: Promise<{ sprintId: string }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { sprintId } = await params;
    const data = await backendFetch<PaginatedResponse<SprintItem>>(
      `/api/v1/sprints/${sprintId}/items`,
      {
        method: "GET",
        headers: getAuthHeader(request),
      }
    );
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail = (error.data as { detail?: string })?.detail || "Failed to load sprint items";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
    const body = (await request.json()) as SprintItemCreate;
    const { sprintId } = await params;
    const data = await backendFetch<SprintItem>(`/api/v1/sprints/${sprintId}/items`, {
      method: "POST",
      headers: getAuthHeader(request),
      body: JSON.stringify(body),
    });
    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail = (error.data as { detail?: string })?.detail || "Failed to create sprint item";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
