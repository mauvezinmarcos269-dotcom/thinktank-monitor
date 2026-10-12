'use client';

import { ProcessingErrorDisclosure } from '@/components/processing-error-disclosure';
import { type AIProgress } from '@/lib/report';
import { aiChunkStatusLabels, aiChunkTypeLabels } from '@/lib/status';

type AIProgressPanelProps = {
  loading: boolean;
  errorMessage: string | null;
  progress: AIProgress | null;
};

export function AIProgressPanel({ loading, errorMessage, progress }: AIProgressPanelProps) {
  return (
    <section className="section-block">
      <h3>AI 分块进度</h3>
      {loading && <p>正在加载 AI 进度……</p>}
      {errorMessage && <p className="message-error">{errorMessage}</p>}
      {progress ? (
        <div className="ai-progress-panel">
          <dl className="ai-progress-overview" aria-label="AI 分块汇总">
            <div>
              <dt>已完成</dt>
              <dd>
                {progress.completed_chunks}
                <small> / {progress.total_chunks}</small>
              </dd>
            </div>
            <div className={progress.failed_chunks > 0 ? 'ai-progress-metric-danger' : undefined}>
              <dt>失败</dt>
              <dd>{progress.failed_chunks}</dd>
            </div>
            <div className={progress.running_chunks > 0 ? 'ai-progress-metric-active' : undefined}>
              <dt>运行中</dt>
              <dd>{progress.running_chunks}</dd>
            </div>
          </dl>

          {progress.latest_error ? (
            <ProcessingErrorDisclosure error={progress.latest_error} operation="ai" label="最近错误" />
          ) : null}

          <div className="ai-progress-types" aria-label="各类分块进度">
            {progress.by_type.map((item) => (
              <section key={item.chunk_type} className="ai-progress-type">
                <div className="ai-progress-type-heading">
                  <strong>{aiChunkTypeLabels[item.chunk_type] ?? item.chunk_type}</strong>
                  <span>
                    成功 {item.success} / {item.total}
                  </span>
                </div>
                <dl>
                  <div>
                    <dt>待处理</dt>
                    <dd>{item.pending}</dd>
                  </div>
                  <div>
                    <dt>已入队</dt>
                    <dd>{item.queued}</dd>
                  </div>
                  <div>
                    <dt>处理中</dt>
                    <dd>{item.processing}</dd>
                  </div>
                  <div className={item.failed > 0 ? 'ai-progress-count-danger' : undefined}>
                    <dt>失败</dt>
                    <dd>{item.failed}</dd>
                  </div>
                </dl>
              </section>
            ))}
          </div>

          {progress.chunks.length > 0 ? (
            <details className="ai-chunk-details">
              <summary>
                <span className="ai-chunk-open-label">查看全部分块</span>
                <span className="ai-chunk-close-label">收起全部分块</span>
              </summary>
              <ol className="ai-chunk-list">
                {progress.chunks.map((chunk) => (
                  <li key={chunk.id} className="ai-chunk-item">
                    <div className="ai-chunk-item-heading">
                      <strong>
                        {aiChunkTypeLabels[chunk.chunk_type] ?? chunk.chunk_type} {chunk.chunk_index}/
                        {chunk.chunk_count}
                      </strong>
                      <span className={`badge ai-chunk-status ai-chunk-status-${chunk.status}`}>
                        {aiChunkStatusLabels[chunk.status] ?? chunk.status}
                      </span>
                    </div>
                    <span className="ai-chunk-retries">重试 {chunk.retry_count} 次</span>
                    {chunk.last_error ? (
                      <ProcessingErrorDisclosure error={chunk.last_error} operation="ai" label="失败原因" compact />
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
  );
}
