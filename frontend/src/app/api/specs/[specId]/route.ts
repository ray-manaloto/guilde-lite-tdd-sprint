import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";
import type { Spec } from "@/types";

const getAuthHeader = (request: NextRequest): Record<string, string> => {
  const accessToken = request.cookies.get("access_token")?.value;
  if (accessToken) {
    return { Authorization: `Bearer ${accessToken}` };
  }
  return {};
};

interface RouteParams {
  params: Promise<{ specId: string }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { specId } = await params;
    const data = await backendFetch<Spec>(`/api/v1/specs/${specId}`, {
      method: "GET",
      headers: getAuthHeader(request),
    });
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail = (error.data as { detail?: string })?.detail || "Failed to load spec";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
