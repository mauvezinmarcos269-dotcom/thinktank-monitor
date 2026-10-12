'use client';

import { type Source, type ThinkTank } from '@/lib/institution';
import { type Report } from '@/lib/report';
import {
  sourceTypeLabels,
} from '@/lib/status';

import {
  formatDateTime,
  formatSourceUrl,
} from './report-page-utils';

type ReportDocumentType = {
  label: string;
  className: string;
  isPdf: boolean;
};

type ReportDetailHeaderProps = {
  report: Report;
  documentType: ReportDocumentType;
  source: Source | null;
  thinkTank: ThinkTank | null;
};

export function ReportDetailHeader({
  report,
  documentType,
  source,
  thinkTank,
}: ReportDetailHeaderProps) {
  return (
    <header className="report-detail-header">
      <div className="detail-heading">
        <div>
          <span className="report-id-badge report-id-badge-large">
            ID {report.id}
          </span>
          <h2>{report.title}</h2>
        </div>
        <a
          className="detail-source-link"
          href={report.url}
          target="_blank"
          rel="noreferrer"
        >
          打开原文
        </a>
      </div>

      <div className="detail-source-context" aria-label="报告来源">
        <span>{thinkTank?.name ?? '未知智库'}</span>
        {thinkTank?.country ? <span>{thinkTank.country}</span> : null}
        {source ? (
          <span>
            {sourceTypeLabels[source.source_type] ?? source.source_type} /{' '}
            {formatSourceUrl(source.url)}
          </span>
        ) : null}
      </div>

      <div className="status-line">
        <span className={documentType.className}>{documentType.label}</span>
        {report.ai_generated_at ? (
          <span className="badge">
            生成：{formatDateTime(report.ai_generated_at)}
          </span>
        ) : null}
        {report.reviewed_at ? (
          <span className="badge">
            复核：{formatDateTime(report.reviewed_at)}
          </span>
        ) : null}
      </div>
    </header>
  );
}

export type { ReportDocumentType };
