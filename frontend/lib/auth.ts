export type CurrentUser = {
  id: number;
  email: string;
  role: 'admin' | 'teacher';
  is_active: boolean;
};

const ACCESS_TOKEN_KEY = 'access_token';
const CURRENT_USER_KEY = 'current_user';

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }

  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
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
    const currentUser = JSON.parse(rawCurrentUser) as CurrentUser;

    if (
      typeof currentUser.id !== 'number' ||
      typeof currentUser.email !== 'string' ||
      (currentUser.role !== 'admin' && currentUser.role !== 'teacher') ||
      typeof currentUser.is_active !== 'boolean'
    ) {
      clearLoginSession();
      return null;
    }

    return currentUser;
  } catch {
    clearLoginSession();
    return null;
  }
}

export function saveLoginSession(
  accessToken: string,
  currentUser: CurrentUser
): void {
  if (typeof window === 'undefined') {
    return;
  }

  sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  sessionStorage.setItem(CURRENT_USER_KEY, JSON.stringify(currentUser));
}

export function clearLoginSession(): void {
  if (typeof window === 'undefined') {
    return;
  }

  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(CURRENT_USER_KEY);
}