import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ThinkTank Monitor',
  description: '\u5168\u7403\u667a\u5e93\u6d89\u534e\u7814\u7a76\u76d1\u6d4b\u5e73\u53f0',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}