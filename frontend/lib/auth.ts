export type CurrentUser = {
  id: string | number; // 兼容后端可能返回的 UUID 字符串或数字
  email: string;
  role: string;
  is_active?: boolean; // 设置为可选字段
};

const ACCESS_TOKEN_KEY = 'access_token';
const CURRENT_USER_KEY = 'current_user';

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const token = sessionStorage.getItem(ACCESS_TOKEN_KEY);
  return token && token.trim() ? token : null;
}

export function getCurrentUser(): CurrentUser | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const rawCurrentUser = sessionStorage.getItem(CURRENT_USER_KEY);
  if (!rawCurrentUser) {
    return null;
  }

  try {
    const currentUser = JSON.parse(rawCurrentUser);
    if (!currentUser || typeof currentUser !== 'object') {
      return null;
    }

    if (
      !('id' in currentUser) ||
      typeof currentUser.email !== 'string' ||
      typeof currentUser.role !== 'string'
    ) {
      return null;
    }

    return currentUser as CurrentUser;
  } catch (error) {
    console.error('[auth] current_user JSON 解析失败:', error);
    return null;
  }
}

export function saveLoginSession(
  accessToken: string,
  currentUser: CurrentUser
): void {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  sessionStorage.setItem(CURRENT_USER_KEY, JSON.stringify(currentUser));
}

export function clearLoginSession(): void {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(CURRENT_USER_KEY);
}
