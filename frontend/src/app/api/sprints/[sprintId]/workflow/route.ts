import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";
import type { Workflow } from "@/types/workflow";

const getAuthHeader = (request: NextRequest): Record<string, string> => {
  const accessToken = request.cookies.get("access_token")?.value;
  if (accessToken) {
    return { Authorization: `Bearer ${accessToken}` };
  }
  return {};
};

interface RouteParams {
  params: Promise<{ sprintId: string }>;
}

/**
 * GET /api/sprints/[sprintId]/workflow
 *
 * Fetches the full workflow state for a sprint including phases,
 * candidates, judge decisions, and timeline events.
 */
export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { sprintId } = await params;
    const data = await backendFetch<Workflow>(`/api/v1/sprints/${sprintId}/workflow`, {
      method: "GET",
      headers: getAuthHeader(request),
    });
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail = (error.data as { detail?: string })?.detail || "Failed to load workflow";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
