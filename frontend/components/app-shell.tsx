'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { ReactNode, useEffect, useState } from 'react';

import {
  clearLoginSession,
  getAccessToken,
  getCurrentUser,
  type CurrentUser,
} from '@/lib/auth';
import { fetchUnreadNotificationCount } from '@/lib/notification';

type AppShellProps = {
  children: ReactNode;
};

const navigationItems = [
  { href: '/dashboard', label: '仪表盘' },
  { href: '/reports', label: '研究报告' },
  { href: '/notifications', label: '通知提醒' },
  { href: '/settings', label: '系统设置' },
];

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();

  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);

  async function refreshUnreadCount() {
    try {
      const count = await fetchUnreadNotificationCount();
      setUnreadCount(count);
    } catch {
      setUnreadCount(0);
    }
  }

  useEffect(() => {
    if (pathname === '/login') {
      setIsCheckingAuth(false);
      return;
    }

    const accessToken = getAccessToken();
    if (!accessToken) {
      clearLoginSession();
      router.replace('/login');
      return;
    }

    const user = getCurrentUser();
    if (!user) {
      clearLoginSession();
      router.replace('/login');
      return;
    }

    if (user.is_active === false) {
      clearLoginSession();
      router.replace('/login');
      return;
    }

    setCurrentUser(user);
    setIsCheckingAuth(false);

    refreshUnreadCount();
  }, [pathname, router]);

  useEffect(() => {
    if (pathname === '/login') {
      return;
    }

    function handleRefresh() {
      refreshUnreadCount();
    }

    window.addEventListener('thinktank:notifications-updated', handleRefresh);
    window.addEventListener('focus', handleRefresh);

    return () => {
      window.removeEventListener('thinktank:notifications-updated', handleRefresh);
      window.removeEventListener('focus', handleRefresh);
    };
  }, [pathname]);

  function handleLogout() {
    clearLoginSession();
    router.replace('/login');
  }

  if (pathname === '/login') {
    return <>{children}</>;
  }

  if (isCheckingAuth) {
    return (
      <main style={{ padding: '2rem' }}>
        <p>正在验证登录状态…</p>
      </main>
    );
  }

  if (!currentUser) {
    return null;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <Link href="/dashboard" className="brand-title">ThinkTank Monitor</Link>
          <span className="brand-subtitle">全球智库涉华研究监测平台</span>
        </div>

        <div className="userbar">
          <span>{currentUser.email}</span>
          <span className="badge">
            {currentUser.role === 'admin' ? '管理员' : '研究用户'}
          </span>
          <button type="button" onClick={handleLogout}>
            退出登录
          </button>
        </div>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <nav aria-label="主导航">
            <ul>
              {navigationItems.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="nav-link"
                    aria-current={pathname === item.href ? 'page' : undefined}
                  >
                    {item.label}
                    {item.href === '/notifications' && unreadCount > 0
                      ? ` (${unreadCount})`
                      : ''}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </aside>

        <main className="main-content">{children}</main>
      </div>
    </div>
  );
}
