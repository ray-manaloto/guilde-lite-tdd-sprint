import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";
import type { SprintItem, SprintItemUpdate } from "@/types";

const getAuthHeader = (request: NextRequest) => {
  const accessToken = request.cookies.get("access_token")?.value;
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
};

interface RouteParams {
  params: { sprintId: string; itemId: string };
}

export async function PATCH(request: NextRequest, { params }: RouteParams) {
  try {
    const body = (await request.json()) as SprintItemUpdate;
    const data = await backendFetch<SprintItem>(
      `/api/v1/sprints/${params.sprintId}/items/${params.itemId}`,
      {
        method: "PATCH",
        headers: getAuthHeader(request),
        body: JSON.stringify(body),
      }
    );
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail = (error.data as { detail?: string })?.detail || "Failed to update sprint item";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    await backendFetch<void>(`/api/v1/sprints/${params.sprintId}/items/${params.itemId}`, {
      method: "DELETE",
      headers: getAuthHeader(request),
    });
    return NextResponse.json(null, { status: 204 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail = (error.data as { detail?: string })?.detail || "Failed to delete sprint item";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
