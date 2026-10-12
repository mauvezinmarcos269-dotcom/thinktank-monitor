import { summarizeReportProcessingError, type ReportProcessingOperation } from '@/lib/report-error';

type ProcessingErrorDisclosureProps = {
  error: string;
  operation: ReportProcessingOperation;
  label: string;
  compact?: boolean;
  tone?: 'danger' | 'neutral';
};

export function ProcessingErrorDisclosure({
  error,
  operation,
  label,
  compact = false,
  tone = 'danger',
}: ProcessingErrorDisclosureProps) {
  const fullError = error.trim();
  const summary = summarizeReportProcessingError(fullError, operation);
  const hasDetails = fullError !== summary;
  const classNames = [
    'processing-error-disclosure',
    compact ? 'processing-error-disclosure-compact' : '',
    tone === 'neutral' ? 'processing-error-disclosure-neutral' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={classNames}>
      <p className="processing-error-summary">
        <strong>{label}：</strong>
        {summary}
      </p>
      {hasDetails ? (
        <details className="processing-error-details">
          <summary>
            <span className="processing-error-open-label">展开详情</span>
            <span className="processing-error-close-label">收起详情</span>
          </summary>
          <div className="processing-error-full">{fullError}</div>
        </details>
      ) : null}
    </div>
  );
}
