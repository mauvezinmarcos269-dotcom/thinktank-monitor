'use client';

import { type AIProgress } from '@/lib/report';
import {
  aiChunkStatusLabels,
  aiChunkTypeLabels,
} from '@/lib/status';

type AIProgressPanelProps = {
  loading: boolean;
  errorMessage: string | null;
  progress: AIProgress | null;
};

export function AIProgressPanel({
  loading,
  errorMessage,
  progress,
}: AIProgressPanelProps) {
  return (
    <section className="section-block">
      <h3>AI 分块进度</h3>
      {loading && <p>正在加载 AI 进度……</p>}
      {errorMessage && <p className="message-error">{errorMessage}</p>}
      {progress ? (
        <div>
          <p>
            已完成 {progress.completed_chunks} / {progress.total_chunks}
            块；失败 {progress.failed_chunks} 块；运行中{' '}
            {progress.running_chunks} 块。
          </p>

          {progress.latest_error && (
            <p className="message-error">最近错误：{progress.latest_error}</p>
          )}

          <ul>
            {progress.by_type.map((item) => (
              <li key={item.chunk_type}>
                {aiChunkTypeLabels[item.chunk_type] ?? item.chunk_type}
                ：成功 {item.success} / {item.total}，待处理 {item.pending}
                ，已入队 {item.queued}，处理中 {item.processing}，失败{' '}
                {item.failed}
              </li>
            ))}
          </ul>

          {progress.chunks.length > 0 ? (
            <details>
              <summary>查看全部分块</summary>
              <ol>
                {progress.chunks.map((chunk) => (
                  <li key={chunk.id}>
                    {aiChunkTypeLabels[chunk.chunk_type] ?? chunk.chunk_type}{' '}
                    {chunk.chunk_index}/{chunk.chunk_count}：
                    {aiChunkStatusLabels[chunk.status] ?? chunk.status}
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
  );
}
