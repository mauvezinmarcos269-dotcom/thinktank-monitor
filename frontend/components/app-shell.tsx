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

type AppShellProps = {
  children: ReactNode;
};

const navigationItems = [
  {
    href: '/dashboard',
    label: '仪表盘',
  },
  {
    href: '/reports',
    label: '研究报告',
  },
  {
    href: '/settings',
    label: '系统设置',
  },
];

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();

  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const accessToken = getAccessToken();
    const user = getCurrentUser();

    if (!accessToken || !user) {
      router.replace('/login');
      return;
    }

    setCurrentUser(user);
    setIsReady(true);
  }, [router]);

  function handleLogout() {
    clearLoginSession();
    router.replace('/login');
  }

  if (!isReady || !currentUser) {
    return <main>正在验证登录状态…</main>;
  }

  return (
    <div>
      <header>
        <div>
          <Link href="/dashboard">ThinkTank Monitor</Link>
          <span>全球智库涉华研究监测平台</span>
        </div>

        <div>
          <span>{currentUser.email}</span>
          <span>{currentUser.role === 'admin' ? '管理员' : '研究用户'}</span>
          <button type="button" onClick={handleLogout}>
            退出登录
          </button>
        </div>
      </header>

      <div>
        <aside>
          <nav aria-label="主导航">
            <ul>
              {navigationItems.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    aria-current={pathname === item.href ? 'page' : undefined}
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </aside>

        <main>{children}</main>
      </div>
    </div>
  );
}