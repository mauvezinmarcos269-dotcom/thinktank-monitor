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
    summary: '第一部分交付稿，重点核对报告核心判断、事实依据和政策建议是否完整。',
    commentary: '第二部分交付稿，重点核对深层现象、战略意图和现实影响是否分析到位。',
    translation: '全文翻译用于逐段核对原文逻辑，也可作为后续归档材料。',
    content: '原文正文用于追溯来源和核对 AI 成果，通常放在最后查看。',
  };
  const readingOrder: ReportView[] = [
    'summary',
    'commentary',
    'translation',
    'content',
  ];
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
        {readingOrder.map((viewKey) => {
          const view = reportViews.find((item) => item.key === viewKey);

          if (!view) {
            return null;
          }

          return (
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
          );
        })}
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
