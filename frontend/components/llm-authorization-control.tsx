'use client';

import { useEffect, useId, useRef, useState } from 'react';

import {
  fetchLLMAuthorizationHistory,
  fetchLLMAuthorizationPreview,
  grantLLMAuthorization,
  revokeLLMAuthorization,
  type LLMAuthorization,
  type LLMAuthorizationPreview,
  type LLMAuthorizationScope,
} from '@/lib/llm-authorization';

type LLMAuthorizationControlProps = {
  scope: LLMAuthorizationScope;
  targetId: number;
  compact?: boolean;
};

const scopeLabels: Record<LLMAuthorizationScope, string> = {
  relevance_sample: '涉华抽样授权',
  report_generation: '全文生成授权',
};

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

export function LLMAuthorizationControl({ scope, targetId, compact = false }: LLMAuthorizationControlProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const dialogTitleId = useId();
  const [preview, setPreview] = useState<LLMAuthorizationPreview | null>(null);
  const [history, setHistory] = useState<LLMAuthorization[]>([]);
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    setPreview(null);
    setHistory([]);
    setConfirmed(false);
    setErrorMessage(null);
    setStatusMessage(null);
  }, [scope, targetId]);

  async function loadAuthorization() {
    setLoading(true);
    setErrorMessage(null);
    try {
      const [nextPreview, nextHistory] = await Promise.all([
        fetchLLMAuthorizationPreview(scope, targetId),
        fetchLLMAuthorizationHistory(scope, targetId),
      ]);
      setPreview(nextPreview);
      setHistory(nextHistory);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '授权信息加载失败。');
    } finally {
      setLoading(false);
    }
  }

  async function openDialog() {
    setPreview(null);
    setHistory([]);
    setConfirmed(false);
    setErrorMessage(null);
    setStatusMessage(null);
    dialogRef.current?.showModal();
    await loadAuthorization();
  }

  function closeDialog() {
    if (!submitting) {
      dialogRef.current?.close();
    }
  }

  async function handleGrant() {
    if (!preview || !confirmed) return;
    setSubmitting(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      await grantLLMAuthorization(preview);
      const [nextPreview, nextHistory] = await Promise.all([
        fetchLLMAuthorizationPreview(scope, targetId),
        fetchLLMAuthorizationHistory(scope, targetId),
      ]);
      setPreview(nextPreview);
      setHistory(nextHistory);
      setConfirmed(false);
      setStatusMessage('授权已记录。');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '授权提交失败。');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRevoke() {
    setSubmitting(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const result = await revokeLLMAuthorization(scope, targetId);
      const [nextPreview, nextHistory] = await Promise.all([
        fetchLLMAuthorizationPreview(scope, targetId),
        fetchLLMAuthorizationHistory(scope, targetId),
      ]);
      setPreview(nextPreview);
      setHistory(nextHistory);
      setConfirmed(false);
      setStatusMessage(result.revoked_count > 0 ? '授权已撤销。' : '当前没有有效授权。');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '授权撤销失败。');
    } finally {
      setSubmitting(false);
    }
  }

  const activeGrant = history.find((item) => item.revoked_at === null);

  return (
    <>
      <button
        type="button"
        className={compact ? 'llm-authorization-trigger compact' : 'llm-authorization-trigger'}
        onClick={openDialog}
      >
        {preview?.authorized ? '查看或撤销授权' : scopeLabels[scope]}
      </button>

      <dialog
        ref={dialogRef}
        className="llm-authorization-dialog"
        aria-labelledby={dialogTitleId}
        onCancel={(event) => {
          if (submitting) event.preventDefault();
        }}
        onClick={(event) => {
          if (event.target === dialogRef.current) closeDialog();
        }}
      >
        <div className="llm-authorization-dialog-header">
          <div>
            <h2 id={dialogTitleId}>{scopeLabels[scope]}</h2>
            <span className={preview?.authorized ? 'badge badge-success' : 'badge'}>
              {preview?.authorized ? '已授权' : '未授权'}
            </span>
          </div>
          <button type="button" onClick={closeDialog} disabled={submitting} aria-label="关闭">
            ×
          </button>
        </div>

        {loading ? <p>正在读取授权信息……</p> : null}
        {errorMessage ? <p className="message-error">{errorMessage}</p> : null}
        {statusMessage ? <p className="message-success">{statusMessage}</p> : null}

        {preview ? (
          <>
            <dl className="llm-authorization-preview">
              <div>
                <dt>文档</dt>
                <dd>{preview.title || '无标题'}</dd>
              </div>
              <div>
                <dt>字符数</dt>
                <dd>{preview.content_length.toLocaleString('zh-CN')}</dd>
              </div>
              <div>
                <dt>发送范围</dt>
                <dd>{preview.data_scope}</dd>
              </div>
              <div>
                <dt>外发总开关</dt>
                <dd>{preview.outbound_enabled ? '已开启' : '已关闭'}</dd>
              </div>
            </dl>

            <details className="llm-authorization-technical">
              <summary>服务与文档版本</summary>
              <dl className="llm-authorization-preview llm-authorization-technical-preview">
                <div>
                  <dt>服务类型</dt>
                  <dd>{preview.provider}</dd>
                </div>
                <div>
                  <dt>服务端点</dt>
                  <dd>{preview.endpoint}</dd>
                </div>
                <div>
                  <dt>模型</dt>
                  <dd>{preview.model}</dd>
                </div>
                <div>
                  <dt>文档版本</dt>
                  <dd>
                    <code>{preview.document_hash}</code>
                  </dd>
                </div>
              </dl>
            </details>

            {!preview.authorized ? (
              <label className="llm-authorization-consent">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(event) => setConfirmed(event.target.checked)}
                  disabled={submitting}
                />
                <span>
                  我确认允许将上述范围的数据发送到所示服务和模型。同意仅适用于当前文档版本和用途。
                  {scope === 'report_generation'
                    ? ' 总开关开启后，后台调度可自动开始处理。'
                    : ' 候选将在后续采集时执行涉华判定。'}
                </span>
              </label>
            ) : null}

            <div className="llm-authorization-actions">
              {preview.authorized ? (
                <button type="button" className="danger-button" onClick={handleRevoke} disabled={submitting}>
                  {submitting ? '撤销中……' : '撤销授权'}
                </button>
              ) : (
                <button type="button" onClick={handleGrant} disabled={!confirmed || submitting}>
                  {submitting ? '提交中……' : '确认授权'}
                </button>
              )}
              <button type="button" className="secondary-button" onClick={closeDialog} disabled={submitting}>
                关闭
              </button>
            </div>

            <details className="llm-authorization-history">
              <summary>授权历史（{history.length}）</summary>
              {history.length === 0 ? (
                <p className="muted">暂无授权记录。</p>
              ) : (
                <ul>
                  {history.map((item) => (
                    <li key={item.id}>
                      <span>{item.revoked_at ? '已撤销' : '有效'}</span>
                      <span>{formatDateTime(item.granted_at)}</span>
                      <code>{item.document_hash.slice(0, 12)}</code>
                    </li>
                  ))}
                </ul>
              )}
            </details>
          </>
        ) : null}

        {!loading && !preview && !errorMessage ? <p className="muted">没有可授权的文档版本。</p> : null}

        {activeGrant && preview?.authorized ? (
          <p className="muted llm-authorization-active">
            当前授权记录 #{activeGrant.id}，批准于 {formatDateTime(activeGrant.granted_at)}。
          </p>
        ) : null}
      </dialog>
    </>
  );
}
