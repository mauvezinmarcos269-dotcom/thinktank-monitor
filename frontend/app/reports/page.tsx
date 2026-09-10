'use client';

import { Suspense, useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';

import { AppShell } from '@/components/app-shell';
import {
  getCurrentUser,
  type CurrentUser,
} from '@/lib/auth';
import {
  downloadReportDocxExport,
  downloadReportExport,
  fetchAIProgress,
  fetchReport,
  fetchReports,
  retryReportAI,
  triggerFetchContent,
  type AIProgress,
  type Report,
} from '@/lib/report';

type ReportView = 'content' | 'translation' | 'summary' | 'commentary';

const reportViewKeys: ReportView[] = [
  'content',
  'translation',
  'summary',
  'commentary',
];

const reportViews: Array<{
  key: ReportView;
  label: string;
  emptyText: string;
}> = [
  {
    key: 'content',
    label: '原文正文',
    emptyText: '暂无正文，请先抓取正文。',
  },
  {
    key: 'translation',
    label: '全文翻译',
    emptyText: '暂无全文翻译，等待 AI 处理完成。',
  },
  {
    key: 'summary',
    label: '观点摘要',
    emptyText: '暂无观点摘要，等待 AI 处理完成。',
  },
  {
    key: 'commentary',
    label: '分析评论',
    emptyText: '暂无分析评论，等待 AI 处理完成。',
  },
];

const PAGE_SIZE = 20;

const crawlStatusLabels: Record<string, string> = {
  pending: '待抓取',
  running: '抓取中',
  success: '已抓取',
  failed: '抓取失败',
};

const aiStatusLabels: Record<string, string> = {
  pending: '待处理',
  running: 'AI 处理中',
  processing: 'AI 处理中',
  success: 'AI 已完成',
  failed: 'AI 失败',
  skipped: '已跳过',
  finalize_queued: '等待生成终稿',
  finalizing: '正在生成终稿',
};

const chunkTypeLabels: Record<string, string> = {
  translation: '全文翻译',
  analysis: '分析笔记',
};

const chunkStatusLabels: Record<string, string> = {
  pending: '待处理',
  queued: '已入队',
  processing: '处理中',
  success: '成功',
  failed: '失败',
};

function getInitialView(value: string | null): ReportView {
  if (value && reportViewKeys.includes(value as ReportView)) {
    return value as ReportView;
  }

  return 'content';
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return '未知';
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function countTextChars(value: string | null): number {
  return value?.trim().length ?? 0;
}

function getDocumentType(report: Report): {
  label: string;
  className: string;
  isPdf: boolean;
} {
  const isPdf = Boolean(report.pdf_url || report.page_count);

  return {
    label: isPdf ? 'PDF 报告' : '网页长文',
    className: isPdf ? 'badge badge-success' : 'badge badge-info',
    isPdf,
  };
}

function ReportsPageContent() {
  const searchParams = useSearchParams();
  const [reports, setReports] = useState<Report[]>([]);
  const [selected, setSelected] = useState<Report | null>(null);
  const [aiProgress, setAIProgress] = useState<AIProgress | null>(null);
  const [activeView, setActiveView] = useState<ReportView>('content');
  const [page, setPage] = useState(1);
  const [totalReports, setTotalReports] = useState(0);

  const [listError, setListError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [progressError, setProgressError] = useState<string | null>(null);
  const [taskMessage, setTaskMessage] = useState<string | null>(null);

  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(false);
  const [submittingFetch, setSubmittingFetch] = useState(false);
  const [submittingAI, setSubmittingAI] = useState(false);
  const [exportingReport, setExportingReport] = useState(false);
  const [exportingDocx, setExportingDocx] = useState(false);


  const [currentUser, setCurrentUser] =
    useState<CurrentUser | null>(null);

  const canFetchContent = currentUser?.role === 'admin';
  const canRetryAI = currentUser?.role === 'admin';


  const loadAIProgress = useCallback(async (reportId: number) => {
    setLoadingProgress(true);
    setProgressError(null);

    try {
      const progress = await fetchAIProgress(reportId);
      setAIProgress(progress);
    } catch (err) {
      setAIProgress(null);
      setProgressError((err as Error).message);
    } finally {
      setLoadingProgress(false);
    }
  }, []);


  const handleSelect = useCallback(async (reportId: number) => {
    setLoadingDetail(true);
    setDetailError(null);
    setProgressError(null);
    setTaskMessage(null);

    try {
      const report = await fetchReport(reportId);
      setSelected(report);
      setActiveView(getInitialView(searchParams.get('view')));
      await loadAIProgress(report.id);
    } catch (err) {
      setDetailError((err as Error).message);
    } finally {
      setLoadingDetail(false);
    }
  }, [loadAIProgress, searchParams]);


  // 页面挂载后读取 sessionStorage 中的用户
  useEffect(() => {
    const user = getCurrentUser();
    setCurrentUser(user);
  }, []);


  // 加载报告列表
  useEffect(() => {
    setLoadingList(true);
    setListError(null);

    fetchReports({
      skip: (page - 1) * PAGE_SIZE,
      limit: PAGE_SIZE,
    })
      .then((data) => {
        setReports(data.items);
        setTotalReports(data.total);

        const reportId = Number(searchParams.get('report_id'));

        if (reportId) {
          handleSelect(reportId);
        }
      })
      .catch((err: Error) => setListError(err.message))
      .finally(() => setLoadingList(false));
  }, [page, searchParams, handleSelect]);

  const totalPages = Math.max(1, Math.ceil(totalReports / PAGE_SIZE));
  const selectedDocumentType = selected ? getDocumentType(selected) : null;

  async function handleFetchContent() {
    if (!selected) {
      return;
    }

    setSubmittingFetch(true);
    setDetailError(null);
    setTaskMessage(null);

    try {
      const response = await triggerFetchContent(selected.id);

      setTaskMessage(
        `${response.message} 任务 ID：${response.task_id ?? '无'}`
      );

      setSelected((current) =>
        current
          ? {
              ...current,
              crawl_status: response.crawl_status,
              crawl_error: null,
              updated_at: response.updated_at,
            }
          : null
      );
    } catch (err) {
      setDetailError((err as Error).message);
    } finally {
      setSubmittingFetch(false);
    }
  }

  async function handleRetryAI() {
    if (!selected) {
      return;
    }

    setSubmittingAI(true);
    setDetailError(null);
    setProgressError(null);
    setTaskMessage(null);

    try {
      const response = await retryReportAI(selected.id);

      setTaskMessage(
        `${response.message} 任务 ID：${response.task_id ?? '无'}`
      );

      setSelected((current) =>
        current
          ? {
              ...current,
              ai_status: response.ai_status,
              updated_at: response.updated_at,
            }
          : null
      );

      await loadAIProgress(selected.id);
    } catch (err) {
      setDetailError((err as Error).message);
    } finally {
      setSubmittingAI(false);
    }
  }

  async function handleExportReport() {
    if (!selected) {
      return;
    }

    setExportingReport(true);
    setDetailError(null);
    setTaskMessage(null);

    try {
      const blob = await downloadReportExport(selected.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${selected.id}-${selected.title.slice(0, 40)}-ai-results.md`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setTaskMessage('报告成果导出已开始下载。');
    } catch (err) {
      setDetailError((err as Error).message);
    } finally {
      setExportingReport(false);
    }
  }

  async function handleExportDocx() {
    if (!selected) {
      return;
    }

    setExportingDocx(true);
    setDetailError(null);
    setTaskMessage(null);

    try {
      const blob = await downloadReportDocxExport(selected.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${selected.id}-${selected.title.slice(0, 40)}-ai-results.docx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setTaskMessage('报告 Word 文档导出已开始下载。');
    } catch (err) {
      setDetailError((err as Error).message);
    } finally {
      setExportingDocx(false);
    }
  }

  return (
    <AppShell>
      <div className="page-header">
        <h1>研究报告</h1>
        <p>查看已收录报告、AI 翻译评论成果和处理进度。</p>
      </div>

      {loadingList && <p>正在加载报告列表……</p>}
      {listError && <p className="message-error">{listError}</p>}

      <div className="split-layout">
        <section className="panel">
          <div className="toolbar">
            <p className="muted">
              共 {totalReports} 篇，第 {page} / {totalPages} 页
            </p>
            <button
              type="button"
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              disabled={page <= 1 || loadingList}
            >
              上一页
            </button>
            <button
              type="button"
              onClick={() =>
                setPage((current) => Math.min(totalPages, current + 1))
              }
              disabled={page >= totalPages || loadingList}
            >
              下一页
            </button>
          </div>

          <ul className="report-list">
            {reports.map((report) => {
              const documentType = getDocumentType(report);

              return (
                <li key={report.id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(report.id)}
                  >
                    <span className="report-title">{report.title}</span>
                    <span className={documentType.className}>
                      {documentType.label}
                    </span>
                    <br />
                    <small>
                      抓取：{crawlStatusLabels[report.crawl_status] ?? report.crawl_status}
                      {' / '}
                      AI：{aiStatusLabels[report.ai_status] ?? report.ai_status}
                    </small>
                  </button>
                </li>
              );
            })}
          </ul>
        </section>

        <section className="panel">
          {loadingDetail && <p>正在加载报告详情……</p>}
          {detailError && (
            <p className="message-error">{detailError}</p>
          )}
          {taskMessage && (
            <p className="message-success">{taskMessage}</p>
          )}

          {selected && selectedDocumentType && !loadingDetail && (
            <article>
              <h2>{selected.title}</h2>
              <p>
                <a
                  href={selected.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  原文链接
                </a>
              </p>

              <div className="status-line">
                <span className={selectedDocumentType.className}>
                  {selectedDocumentType.label}
                </span>
                <span className="badge">
                  抓取：{crawlStatusLabels[selected.crawl_status] ?? selected.crawl_status}
                </span>
                <span className="badge">
                  AI：{aiStatusLabels[selected.ai_status] ?? selected.ai_status}
                </span>
                {selected.ai_generated_at ? (
                  <span className="badge">
                    生成：{formatDateTime(selected.ai_generated_at)}
                  </span>
                ) : null}
              </div>

              <dl className="metadata-grid">
                <div>
                  <dt>PDF 链接</dt>
                  <dd>
                    {selectedDocumentType.isPdf && selected.pdf_url ? (
                      <a
                        href={selected.pdf_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        打开 PDF
                      </a>
                    ) : selectedDocumentType.isPdf ? (
                      '暂无'
                    ) : (
                      '网页正文'
                    )}
                  </dd>
                </div>

                <div>
                  <dt>页数</dt>
                  <dd>
                    {selectedDocumentType.isPdf
                      ? selected.page_count ?? '未知'
                      : '不适用'}
                  </dd>
                </div>

                <div>
                  <dt>有效文本页</dt>
                  <dd>
                    {selectedDocumentType.isPdf
                      ? selected.non_empty_page_count ?? '未知'
                      : '不适用'}
                  </dd>
                </div>

                <div>
                  <dt>PDF 大小</dt>
                  <dd>
                    {selectedDocumentType.isPdf && selected.pdf_byte_length
                      ? `${Math.round(selected.pdf_byte_length / 1024)} KB`
                      : selectedDocumentType.isPdf
                        ? '未知'
                        : '不适用'}
                  </dd>
                </div>

                <div>
                  <dt>成果字数</dt>
                  <dd>
                    原文 {countTextChars(selected.content)} 字 / 翻译{' '}
                    {countTextChars(selected.translation)} 字 / 摘要{' '}
                    {countTextChars(selected.summary)} 字 / 评论{' '}
                    {countTextChars(selected.commentary)} 字
                  </dd>
                </div>
              </dl>

              {canFetchContent && (
                <button
                  type="button"
                  onClick={handleFetchContent}
                  disabled={submittingFetch}
                >
                  {submittingFetch ? '正在提交抓取任务……' : '抓取正文'}
                </button>
              )}

              {canRetryAI && selected.content && (
                <button
                  type="button"
                  onClick={handleRetryAI}
                  disabled={
                    submittingAI ||
                    ['processing', 'finalize_queued', 'finalizing'].includes(
                      selected.ai_status
                    )
                  }
                >
                  {submittingAI ? '正在提交 AI 任务……' : '重试 AI 处理'}
                </button>
              )}

              <button
                type="button"
                onClick={handleExportReport}
                disabled={exportingReport}
              >
                {exportingReport ? '正在导出……' : '导出成果 Markdown'}
              </button>

              <button
                type="button"
                onClick={handleExportDocx}
                disabled={exportingDocx}
              >
                {exportingDocx ? '正在导出 Word……' : '导出成果 Word'}
              </button>

              {selected.crawl_error && (
                <p style={{ color: 'red' }}>
                  抓取错误：{selected.crawl_error}
                </p>
              )}

              <section className="section-block">
                <h3>AI 分块进度</h3>
                {loadingProgress && <p>正在加载 AI 进度……</p>}
                {progressError && (
                  <p className="message-error">{progressError}</p>
                )}
                {aiProgress ? (
                  <div>
                    <p>
                      已完成 {aiProgress.completed_chunks} /{' '}
                      {aiProgress.total_chunks} 块；失败{' '}
                      {aiProgress.failed_chunks} 块；运行中{' '}
                      {aiProgress.running_chunks} 块。
                    </p>

                    {aiProgress.latest_error && (
                      <p style={{ color: 'red' }}>
                        最近错误：{aiProgress.latest_error}
                      </p>
                    )}

                    <ul>
                      {aiProgress.by_type.map((item) => (
                        <li key={item.chunk_type}>
                          {chunkTypeLabels[item.chunk_type] ?? item.chunk_type}
                          ：成功 {item.success} / {item.total}，待处理{' '}
                          {item.pending}，已入队 {item.queued}，处理中{' '}
                          {item.processing}，失败 {item.failed}
                        </li>
                      ))}
                    </ul>

                    {aiProgress.chunks.length > 0 ? (
                      <details>
                        <summary>查看全部分块</summary>
                        <ol>
                          {aiProgress.chunks.map((chunk) => (
                            <li key={chunk.id}>
                              {chunkTypeLabels[chunk.chunk_type] ??
                                chunk.chunk_type}{' '}
                              {chunk.chunk_index}/{chunk.chunk_count}：
                              {chunkStatusLabels[chunk.status] ??
                                chunk.status}
                              ，重试 {chunk.retry_count} 次
                              {chunk.last_error ? (
                                <span className="message-error">
                                  {' '}
                                  / {chunk.last_error}
                                </span>
                              ) : null}
                            </li>
                          ))}
                        </ol>
                      </details>
                    ) : (
                      <p>暂无 AI 分块记录。</p>
                    )}
                  </div>
                ) : null}
              </section>

              <hr />

              <div className="tabbar" role="tablist" aria-label="报告内容视图">
                {reportViews.map((view) => (
                  <button
                    key={view.key}
                    type="button"
                    role="tab"
                    aria-selected={activeView === view.key}
                    onClick={() => setActiveView(view.key)}
                  >
                    {view.label}
                  </button>
                ))}
              </div>

              {selected[activeView] ? (
                <div className="content-view">
                  {selected[activeView]}
                </div>
              ) : (
                <p>
                  {
                    reportViews.find(
                      (view) => view.key === activeView
                    )?.emptyText
                  }
                </p>
              )}
            </article>
          )}
        </section>
      </div>
    </AppShell>
  );
}

export default function ReportsPage() {
  return (
    <Suspense
      fallback={
        <AppShell>
          <p>正在加载报告列表……</p>
        </AppShell>
      }
    >
      <ReportsPageContent />
    </Suspense>
  );
}
