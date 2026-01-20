/**
 * Client-side API client.
 * All requests go through Next.js API routes (/api/*), never directly to the backend.
 * This keeps the backend URL hidden from the browser.
 */

export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public data?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  params?: Record<string, string>;
  body?: unknown;
}

const formatValidationDetail = (detail: unknown): string | null => {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((entry) => {
        if (typeof entry === "string") return entry;
        if (entry && typeof entry === "object") {
          const entryRecord = entry as { msg?: unknown; loc?: unknown };
          const msg = typeof entryRecord.msg === "string" ? entryRecord.msg : null;
          const loc = Array.isArray(entryRecord.loc)
            ? entryRecord.loc.map((value) => String(value)).join(".")
            : null;
          if (msg && loc) return `${loc}: ${msg}`;
          if (msg) return msg;
        }
        return null;
      })
      .filter((message): message is string => Boolean(message));
    return messages.length ? messages.join("; ") : null;
  }
  if (detail && typeof detail === "object") {
    const entryRecord = detail as { msg?: unknown };
    if (typeof entryRecord.msg === "string") {
      return entryRecord.msg;
    }
  }
  return null;
};

const formatErrorMessage = (errorData: unknown): string => {
  if (!errorData) return "Request failed";
  if (typeof errorData === "string") return errorData;
  if (Array.isArray(errorData)) {
    const message = formatValidationDetail(errorData);
    return message || "Request failed";
  }
  if (typeof errorData === "object") {
    const record = errorData as { detail?: unknown; message?: unknown };
    const detailMessage = formatValidationDetail(record.detail);
    if (detailMessage) return detailMessage;
    if (typeof record.message === "string") return record.message;
    const message = formatValidationDetail(record.message);
    if (message) return message;
  }
  return "Request failed";
};

class ApiClient {
  private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { params, body, ...fetchOptions } = options;

    let url = `/api${endpoint}`;

    if (params) {
      const searchParams = new URLSearchParams(params);
      url += `?${searchParams.toString()}`;
    }

    const response = await fetch(url, {
      ...fetchOptions,
      headers: {
        "Content-Type": "application/json",
        ...fetchOptions.headers,
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = null;
      }
      const message = formatErrorMessage(errorData);
      throw new ApiError(
        response.status,
        message,
        errorData
      );
    }

    // Handle empty responses
    const text = await response.text();
    if (!text) {
      return null as T;
    }

    return JSON.parse(text);
  }

  get<T>(endpoint: string, options?: RequestOptions) {
    return this.request<T>(endpoint, { ...options, method: "GET" });
  }

  post<T>(endpoint: string, body?: unknown, options?: RequestOptions) {
    return this.request<T>(endpoint, { ...options, method: "POST", body });
  }

  put<T>(endpoint: string, body?: unknown, options?: RequestOptions) {
    return this.request<T>(endpoint, { ...options, method: "PUT", body });
  }

  patch<T>(endpoint: string, body?: unknown, options?: RequestOptions) {
    return this.request<T>(endpoint, { ...options, method: "PATCH", body });
  }

  delete<T>(endpoint: string, options?: RequestOptions) {
    return this.request<T>(endpoint, { ...options, method: "DELETE" });
  }
}

export const apiClient = new ApiClient();
