'use client';

import { type Report } from '@/lib/report';

import {
  countTextChars,
  reportViews,
  type CopyTarget,
  type ReportView,
} from './report-page-utils';

type ReportContentViewerProps = {
  report: Report;
  activeView: ReportView;
  copyingTarget: CopyTarget | null;
  onActiveViewChange: (view: ReportView) => void;
  onCopyCurrent: () => void;
};

export function ReportContentViewer({
  report,
  activeView,
  copyingTarget,
  onActiveViewChange,
  onCopyCurrent,
}: ReportContentViewerProps) {
  const activeText = report[activeView];
  const activeTextCount = countTextChars(activeText);
  const activeViewConfig = reportViews.find((view) => view.key === activeView);
  const guidance: Record<ReportView, string> = {
    content: '原文正文用于核对 AI 成果，篇幅较长时可优先阅读主要观点和深层研判。',
    translation: '全文翻译保留原报告主要内容，适合需要细读原文逻辑时使用。',
    summary: '主要观点适合快速把握报告核心判断、事实依据和政策建议。',
    commentary: '深层研判用于理解报告背后的战略意图、政策含义和潜在影响。',
  };
  const getViewCount = (view: ReportView) => countTextChars(report[view]);
  const getViewStatus = (view: ReportView) => {
    const count = getViewCount(view);
    return count > 0 ? `${count} 字` : '未生成';
  };
  const getTabClassName = (view: ReportView) => {
    if (activeView === view) {
      return 'content-tab content-tab-active';
    }

    if (getViewCount(view) === 0) {
      return 'content-tab content-tab-empty';
    }

    return 'content-tab content-tab-ready';
  };

  return (
    <section className="content-reader" aria-label="报告内容阅读区">
      <div className="content-heading">
        <div>
          <h3>{activeViewConfig?.label ?? '报告内容'}</h3>
          <p>{guidance[activeView]}</p>
        </div>
        <button
          type="button"
          onClick={onCopyCurrent}
          disabled={copyingTarget !== null || activeTextCount === 0}
        >
          {copyingTarget === 'current' ? '正在复制……' : '复制当前内容'}
        </button>
      </div>

      <div className="tabbar" role="tablist" aria-label="报告内容视图">
        {reportViews.map((view) => (
          <button
            key={view.key}
            type="button"
            role="tab"
            className={getTabClassName(view.key)}
            aria-selected={activeView === view.key}
            onClick={() => onActiveViewChange(view.key)}
          >
            <span>{view.label}</span>
            <small>{getViewStatus(view.key)}</small>
          </button>
        ))}
      </div>

      {activeText ? (
        <div className="content-view">{activeText}</div>
      ) : (
        <div className="empty-state">
          <strong>{activeViewConfig?.label ?? '报告内容'}暂不可读</strong>
          <p>{activeViewConfig?.emptyText}</p>
        </div>
      )}
    </section>
  );
}
