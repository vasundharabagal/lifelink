/**
 * Typed API client for LIFELINK.
 * Uses httpOnly SameSite=Strict cookie session (ll_session).
 * Never stores tokens in localStorage — always credentials: "include".
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
    public readonly code?: string
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

async function parseError(res: Response): Promise<never> {
  let detail = `HTTP ${res.status}`;
  let code: string | undefined;
  try {
    const body = await res.json();
    if (typeof body.detail === 'string') {
      detail = body.detail;
    } else if (Array.isArray(body.detail)) {
      // FastAPI validation error array
      detail = body.detail.map((e: { msg: string }) => e.msg).join('; ');
    }
    if (body.code) code = body.code;
  } catch {
    // ignore JSON parse errors
  }
  throw new ApiError(res.status, detail, code);
}

async function request<T>(
  method: string,
  url: string,
  body?: unknown,
  extraHeaders?: Record<string, string>
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...extraHeaders,
  };

  const res = await fetch(`${BASE_URL}${url}`, {
    method,
    headers,
    credentials: 'include',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    await parseError(res);
  }

  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(url: string) => request<T>('GET', url),
  post: <T>(url: string, body?: unknown, headers?: Record<string, string>) =>
    request<T>('POST', url, body, headers),
  patch: <T>(url: string, body?: unknown) => request<T>('PATCH', url, body),
  delete: <T>(url: string) => request<T>('DELETE', url),
};
