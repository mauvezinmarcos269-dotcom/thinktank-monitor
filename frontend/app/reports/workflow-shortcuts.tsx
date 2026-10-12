'use client';

import { type ReportWorkflowShortcut } from './report-filter-bar';

type WorkflowShortcutsProps = {
  activeShortcut: ReportWorkflowShortcut | '';
  loading: boolean;
  onWorkflowShortcut: (shortcut: ReportWorkflowShortcut) => void;
  onResetFilters: () => void;
};

export function WorkflowShortcuts({
  activeShortcut,
  loading,
  onWorkflowShortcut,
  onResetFilters,
}: WorkflowShortcutsProps) {
  return (
    <div className="workflow-shortcuts" aria-label="常用工作流筛选">
      <button
        type="button"
        onClick={() => onWorkflowShortcut('teacher_review')}
        aria-pressed={activeShortcut === 'teacher_review'}
        disabled={loading}
      >
        <span>待老师复核</span>
        <small>待复核 / AI 完成 / 成果齐全</small>
      </button>
      <button
        type="button"
        onClick={() => onWorkflowShortcut('ready_export')}
        aria-pressed={activeShortcut === 'ready_export'}
        disabled={loading}
      >
        <span>可直接导出</span>
        <small>AI 完成 / 成果齐全</small>
      </button>
      <button
        type="button"
        onClick={() => onWorkflowShortcut('needs_rerun')}
        aria-pressed={activeShortcut === 'needs_rerun'}
        disabled={loading}
      >
        <span>需重新处理</span>
        <small>复核标记需重跑</small>
      </button>
      <button
        type="button"
        onClick={onResetFilters}
        aria-pressed={activeShortcut === 'all'}
        disabled={loading}
      >
        <span>全部报告</span>
        <small>清空筛选</small>
      </button>
    </div>
  );
}
