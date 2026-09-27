import { getAccessToken } from '@/lib/auth';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000';

type ApiErrorResponse = {
  detail?: string;
};

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAccessToken();

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token
        ? {
            Authorization: `Bearer ${token}`,
          }
        : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    let message = `请求失败：${response.status}`;

    try {
      const errorBody = (await response.json()) as ApiErrorResponse;

      if (errorBody.detail) {
        message = errorBody.detail;
      }
    } catch {
      // 非 JSON 响应
    }

    throw new ApiError(response.status, message);
  }

  return response.json() as Promise<T>;
}

export async function apiDownload(
  path: string,
  options: RequestInit = {}
): Promise<Blob> {
  const token = getAccessToken();

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(token
        ? {
            Authorization: `Bearer ${token}`,
          }
        : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    let message = `请求失败：${response.status}`;

    try {
      const errorBody = (await response.json()) as ApiErrorResponse;

      if (errorBody.detail) {
        message = errorBody.detail;
      }
    } catch {
      // 非 JSON 响应
    }

    throw new ApiError(response.status, message);
  }

  return response.blob();
}

export { API_BASE_URL };
