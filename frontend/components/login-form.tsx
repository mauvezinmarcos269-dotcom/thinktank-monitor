'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';

import { API_BASE_URL } from '@/lib/api';
import { saveLoginSession, type CurrentUser } from '@/lib/auth';

type LoginResponse = {
  access_token: string;
  token_type: string;
};

type ErrorResponse = {
  detail?: string;
};

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function getErrorMessage(response: Response): Promise<string> {
    try {
      const data = (await response.json()) as ErrorResponse;

      if (data.detail) {
        return data.detail;
      }
    } catch {
      // 服务端未返回 JSON 时使用默认提示。
    }

    return '登录失败，请检查邮箱和密码。';
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setErrorMessage('');
    setIsSubmitting(true);

    try {
      const formData = new URLSearchParams({
        username: email.trim(),
        password,
      });

      const loginResponse = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData.toString(),
      });

      if (!loginResponse.ok) {
        throw new Error(await getErrorMessage(loginResponse));
      }

      const loginData = (await loginResponse.json()) as LoginResponse;

      if (!loginData.access_token) {
        throw new Error('登录服务返回的数据不完整，请稍后重试。');
      }

      const meResponse = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
        headers: {
          Authorization: `Bearer ${loginData.access_token}`,
        },
      });

      if (!meResponse.ok) {
        throw new Error('登录状态验证失败，请重新登录。');
      }

      const currentUser = (await meResponse.json()) as CurrentUser;

      saveLoginSession(loginData.access_token, currentUser);

      router.push('/dashboard');
    } catch (error) {
      console.error('[LoginForm] 登录流程异常:', error);
      setErrorMessage(
        error instanceof Error ? error.message : '登录失败，请稍后重试。'
      );
      setIsSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-panel">
        <h1>ThinkTank Monitor</h1>
        <p>登录全球智库涉华研究监测平台</p>

        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="email">邮箱</label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="name@example.com"
              required
              disabled={isSubmitting}
            />
          </div>

          <div className="form-field">
            <label htmlFor="password">密码</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="请输入密码"
              required
              disabled={isSubmitting}
            />
          </div>

          {errorMessage ? (
            <p className="message-error" role="alert">
              {errorMessage}
            </p>
          ) : null}

          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? '正在登录…' : '登录'}
          </button>
        </form>
      </section>
    </main>
  );
}
