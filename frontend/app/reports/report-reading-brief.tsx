'use client';

import { type Report } from '@/lib/report';
import {
  reportAIStatusLabels,
  reportReviewStatusLabels,
} from '@/lib/status';

import {
  countTextChars,
  getReportWorkflowState,
  isAIProcessing,
  type ReportView,
} from './report-page-utils';

type ReportReadingBriefProps = {
  report: Report;
  onViewSelect: (view: ReportView) => void;
};

function getNextStep(report: Report): {
  label: string;
  detail: string;
  targetView: ReportView | null;
} {
  const hasSummary = countTextChars(report.summary) > 0;
  const hasCommentary = countTextChars(report.commentary) > 0;
  const hasTranslation = countTextChars(report.translation) > 0;
  const hasContent = countTextChars(report.content) > 0;

  if (report.review_status === 'approved') {
    return {
      label: '可交付',
      detail: '优先导出 Word 或复制评论稿归档。',
      targetView: hasSummary ? 'summary' : hasCommentary ? 'commentary' : null,
    };
  }

  if (report.review_status === 'needs_rerun') {
    return {
      label: '看复核意见',
      detail: '先确认需重跑原因，再决定是否重新生成 AI 成果。',
      targetView: null,
    };
  }

  if (report.review_status === 'rejected') {
    return {
      label: '无需交付',
      detail: '该报告已标记为不采用，仅保留来源和处理记录。',
      targetView: null,
    };
  }

  if (hasSummary) {
    return {
      label: '先读主要观点',
      detail: '快速判断报告核心结论，再进入深层研判核对分析质量。',
      targetView: 'summary',
    };
  }

  if (hasCommentary) {
    return {
      label: '先读深层研判',
      detail: '主要观点尚未生成完整时，先检查深层分析是否可用。',
      targetView: 'commentary',
    };
  }

  if (hasTranslation) {
    return {
      label: '先读全文翻译',
      detail: '评论稿尚未生成时，可先确认翻译是否完整可靠。',
      targetView: 'translation',
    };
  }

  if (isAIProcessing(report)) {
    return {
      label: '等待 AI 成果',
      detail: '系统正在生成翻译和评论稿，完成后再进入复核。',
      targetView: null,
    };
  }

  if (hasContent) {
    return {
      label: '可触发 AI',
      detail: '正文已抓取，可在下方维护区进入或重试 AI 处理。',
      targetView: 'content',
    };
  }

  return {
    label: '先抓取正文',
    detail: '暂无可读正文，需要管理员先抓取原文内容。',
    targetView: null,
  };
}

export function ReportReadingBrief({
  report,
  onViewSelect,
}: ReportReadingBriefProps) {
  const workflow = getReportWorkflowState(report);
  const nextStep = getNextStep(report);
  const summaryCount = countTextChars(report.summary);
  const commentaryCount = countTextChars(report.commentary);
  const translationCount = countTextChars(report.translation);
  const deliverableReady = summaryCount > 0 || commentaryCount > 0;

  return (
    <section className="reading-brief" aria-label="本篇处理提示">
      <div>
        <span className={workflow.className}>{workflow.label}</span>
        <strong>{nextStep.label}</strong>
        <p>{nextStep.detail}</p>
      </div>
      <dl>
        <div>
          <dt>复核状态</dt>
          <dd>
            {reportReviewStatusLabels[report.review_status] ??
              report.review_status}
          </dd>
        </div>
        <div>
          <dt>AI 状态</dt>
          <dd>{reportAIStatusLabels[report.ai_status] ?? report.ai_status}</dd>
        </div>
        <div>
          <dt>成果状态</dt>
          <dd>
            评论稿 {deliverableReady ? '可读' : '未完成'} / 翻译{' '}
            {translationCount > 0 ? '可读' : '未完成'}
          </dd>
        </div>
      </dl>
      {nextStep.targetView ? (
        <button type="button" onClick={() => onViewSelect(nextStep.targetView!)}>
          去处理
        </button>
      ) : null}
    </section>
  );
}
