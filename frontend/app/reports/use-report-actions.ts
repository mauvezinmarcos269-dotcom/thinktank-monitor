'use client';

import { type Dispatch, type SetStateAction, useState } from 'react';

import {
  batchUpdateReportReviewStatus,
  downloadBatchReportExport,
  downloadReportDocxExport,
  downloadReportExport,
  updateReport,
  type Report,
  type ReportBatchExportFormat,
} from '@/lib/report';
import { type ReportReviewStatus } from '@/lib/status';

import {
  buildCommentaryText,
  type CopyTarget,
  type ReportView,
} from './report-page-utils';

type UseReportActionsParams = {
  selected: Report | null;
  activeView: ReportView;
  selectedReportIds: Set<number>;
  reviewNoteDraft: string;
  setSelected: Dispatch<SetStateAction<Report | null>>;
  setReports: Dispatch<SetStateAction<Report[]>>;
  setSelectedReportIds: Dispatch<SetStateAction<Set<number>>>;
  setDetailError: Dispatch<SetStateAction<string | null>>;
  setListError: Dispatch<SetStateAction<string | null>>;
  setTaskMessage: Dispatch<SetStateAction<string | null>>;
  loadReviewEvents: (reportId: number) => Promise<void>;
};

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function copyTextToClipboard(text: string) {
  if (!navigator.clipboard?.writeText) {
    throw new Error('当前浏览器不支持剪贴板复制。');
  }

  await navigator.clipboard.writeText(text);
}

export function useReportActions({
  selected,
  activeView,
  selectedReportIds,
  reviewNoteDraft,
  setSelected,
  setReports,
  setSelectedReportIds,
  setDetailError,
  setListError,
  setTaskMessage,
  loadReviewEvents,
}: UseReportActionsParams) {
  const [exportingReport, setExportingReport] = useState(false);
  const [exportingDocx, setExportingDocx] = useState(false);
  const [exportingBatchFormat, setExportingBatchFormat] =
    useState<ReportBatchExportFormat | null>(null);
  const [copyingTarget, setCopyingTarget] = useState<CopyTarget | null>(null);
  const [batchReviewStatus, setBatchReviewStatus] = useState<
    ReportReviewStatus | ''
  >('');
  const [submittingBatchReview, setSubmittingBatchReview] = useState(false);
  const [updatingReview, setUpdatingReview] = useState(false);

  async function handleExportReport() {
    if (!selected) {
      return;
    }

    setExportingReport(true);
    setDetailError(null);
    setTaskMessage(null);

    try {
      const blob = await downloadReportExport(selected.id);
      downloadBlob(
        blob,
        `${selected.id}-${selected.title.slice(0, 40)}-ai-results.md`
      );
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
      downloadBlob(
        blob,
        `${selected.id}-${selected.title.slice(0, 40)}-ai-results.docx`
      );
      setTaskMessage('报告 Word 文档导出已开始下载。');
    } catch (err) {
      setDetailError((err as Error).message);
    } finally {
      setExportingDocx(false);
    }
  }

  async function handleBatchExport(format: ReportBatchExportFormat) {
    if (selectedReportIds.size === 0) {
      return;
    }

    setExportingBatchFormat(format);
    setListError(null);
    setTaskMessage(null);

    try {
      const blob = await downloadBatchReportExport(
        Array.from(selectedReportIds),
        format
      );
      downloadBlob(blob, `thinktank-reports-${format}-${Date.now()}.zip`);
      setTaskMessage(`已开始下载 ${selectedReportIds.size} 篇报告成果。`);
    } catch (err) {
      setListError((err as Error).message);
    } finally {
      setExportingBatchFormat(null);
    }
  }

  async function handleCopyReportText(target: CopyTarget) {
    if (!selected) {
      return;
    }

    const text =
      target === 'commentary'
        ? buildCommentaryText(selected)
        : target === 'translation'
          ? selected.translation?.trim() || ''
          : String(selected[activeView] ?? '').trim();

    if (!text) {
      setDetailError('当前内容为空，无法复制。');
      return;
    }

    setCopyingTarget(target);
    setDetailError(null);
    setTaskMessage(null);

    try {
      await copyTextToClipboard(text);
      setTaskMessage('内容已复制到剪贴板。');
    } catch (err) {
      setDetailError((err as Error).message);
    } finally {
      setCopyingTarget(null);
    }
  }

  async function handleReviewStatusChange(value: ReportReviewStatus) {
    if (!selected) {
      return;
    }

    setUpdatingReview(true);
    setDetailError(null);
    setTaskMessage(null);

    try {
      const updated = await updateReport(selected.id, {
        review_status: value,
        review_note: reviewNoteDraft,
      });

      setSelected(updated);
      setReports((current) =>
        current.map((report) => (report.id === updated.id ? updated : report))
      );
      await loadReviewEvents(updated.id);
      setTaskMessage('复核状态已更新。');
    } catch (err) {
      setDetailError((err as Error).message);
    } finally {
      setUpdatingReview(false);
    }
  }

  async function handleReviewNoteSave() {
    if (!selected) {
      return;
    }

    setUpdatingReview(true);
    setDetailError(null);
    setTaskMessage(null);

    try {
      const updated = await updateReport(selected.id, {
        review_note: reviewNoteDraft,
      });

      setSelected(updated);
      setReports((current) =>
        current.map((report) => (report.id === updated.id ? updated : report))
      );
      await loadReviewEvents(updated.id);
      setTaskMessage('复核意见已保存。');
    } catch (err) {
      setDetailError((err as Error).message);
    } finally {
      setUpdatingReview(false);
    }
  }

  async function handleBatchReviewStatusChange() {
    if (!batchReviewStatus || selectedReportIds.size === 0) {
      return;
    }

    setSubmittingBatchReview(true);
    setListError(null);
    setTaskMessage(null);

    try {
      const response = await batchUpdateReportReviewStatus(
        Array.from(selectedReportIds),
        batchReviewStatus
      );

      setReports((current) =>
        current.map((report) =>
          response.items.find((updated) => updated.id === report.id) ?? report
        )
      );
      setSelected((current) =>
        current
          ? response.items.find((updated) => updated.id === current.id) ??
            current
          : current
      );
      setSelectedReportIds(new Set());
      setTaskMessage(
        response.not_found_ids.length > 0
          ? `已更新 ${response.updated_count} 篇，${response.not_found_ids.length} 篇未找到。`
          : `已更新 ${response.updated_count} 篇报告。`
      );
    } catch (err) {
      setListError((err as Error).message);
    } finally {
      setSubmittingBatchReview(false);
    }
  }

  return {
    exportingReport,
    exportingDocx,
    exportingBatchFormat,
    copyingTarget,
    batchReviewStatus,
    submittingBatchReview,
    updatingReview,
    setBatchReviewStatus,
    handleExportReport,
    handleExportDocx,
    handleBatchExport,
    handleCopyReportText,
    handleReviewStatusChange,
    handleReviewNoteSave,
    handleBatchReviewStatusChange,
  };
}
