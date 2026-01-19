import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";
import type { SprintUpdate, SprintWithItems } from "@/types";

const getAuthHeader = (request: NextRequest) => {
  const accessToken = request.cookies.get("access_token")?.value;
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
};

interface RouteParams {
  params: { sprintId: string };
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const data = await backendFetch<SprintWithItems>(`/api/v1/sprints/${params.sprintId}`, {
      method: "GET",
      headers: getAuthHeader(request),
    });
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail = (error.data as { detail?: string })?.detail || "Failed to load sprint";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

export async function PATCH(request: NextRequest, { params }: RouteParams) {
  try {
    const body = (await request.json()) as SprintUpdate;
    const data = await backendFetch<SprintWithItems>(`/api/v1/sprints/${params.sprintId}`, {
      method: "PATCH",
      headers: getAuthHeader(request),
      body: JSON.stringify(body),
    });
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail = (error.data as { detail?: string })?.detail || "Failed to update sprint";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    await backendFetch<void>(`/api/v1/sprints/${params.sprintId}`, {
      method: "DELETE",
      headers: getAuthHeader(request),
    });
    return NextResponse.json(null, { status: 204 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail = (error.data as { detail?: string })?.detail || "Failed to delete sprint";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
