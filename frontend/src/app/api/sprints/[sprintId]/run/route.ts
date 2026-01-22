import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";

const getAuthHeader = (request: NextRequest) => {
  const accessToken = request.cookies.get("access_token")?.value;
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
};

interface RouteParams {
  params: Promise<{ sprintId: string }>;
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
    const { sprintId } = await params;
    const mode = request.nextUrl.searchParams.get("mode");
    const data = await backendFetch(`/api/v1/sprints/${sprintId}/run`, {
      method: "POST",
      headers: getAuthHeader(request),
      params: mode ? { mode } : undefined,
    });
    return NextResponse.json(data, { status: 202 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail =
        (error.data as { detail?: string })?.detail || "Failed to start sprint runner";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
