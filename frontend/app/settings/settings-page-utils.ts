import {
  type SourceCreateInput,
  type SourceHealth,
} from '@/lib/institution';
import { type CrawlRunStatus } from '@/lib/status';

export const sourceTypeOptions: Array<{
  value: SourceCreateInput['source_type'];
  label: string;
}> = [
  { value: 'rss', label: 'RSS' },
  { value: 'website', label: '官网/列表页' },
  { value: 'report_library', label: '报告库' },
  { value: 'topic_page', label: '专题页' },
];

export const crawlableSourceTypes = new Set<SourceCreateInput['source_type']>([
  'rss',
  'website',
]);

export const healthLabels: Record<SourceHealth['health_status'], string> = {
  healthy: '正常',
  warning: '需关注',
  failed: '失败',
  never: '未抓取',
  disabled: '停用',
};

export const healthBadgeClasses: Record<
  SourceHealth['health_status'],
  string
> = {
  healthy: 'badge badge-success',
  warning: 'badge badge-warning',
  failed: 'badge badge-danger',
  never: 'badge',
  disabled: 'badge',
};

export const rolloutStageLabels: Record<string, string> = {
  pilot_crawl: '试运行',
  discovery_only: '仅发现',
  blocked: '阻塞',
  standard_review: '待复核',
};

export const rolloutStageBadgeClasses: Record<string, string> = {
  pilot_crawl: 'badge badge-success',
  discovery_only: 'badge badge-warning',
  blocked: 'badge badge-danger',
  standard_review: 'badge',
};

export const documentPolicyLabels: Record<string, string> = {
  pdf_20_page_required: '20页PDF',
  web_article_allowed: '网页长文',
  source_access_blocked: '入口不可达',
};

export const crawlRunBadgeClasses: Record<CrawlRunStatus, string> = {
  pending: 'badge',
  running: 'badge badge-warning',
  success: 'badge badge-success',
  failed: 'badge badge-danger',
};

export const candidateReasonOptions = [
  '无效 URL',
  '同一来源内重复',
  '已入库重复',
  'PDF 获取或页数/文本检查失败',
  '涉华判断失败',
  '非涉华',
  '并发重复入库',
];

export const candidatePageSize = 50;

const diagnosisWeight: Record<string, number> = {
  document_gate_failed: 0,
  relevance_gate_failed: 1,
  non_china_candidates: 2,
  no_candidates: 3,
  duplicate_candidates: 4,
  no_reports_saved: 5,
  parser: 6,
  http_status: 7,
  network: 8,
  short_pdf: 9,
  ai_queue: 10,
};

export function formatDateTime(value: string | null): string {
  if (!value) {
    return '暂无';
  }

  return new Date(value).toLocaleString('zh-CN', {
    hour12: false,
  });
}

export function formatDuration(value: number | null): string {
  if (value === null) {
    return '暂无';
  }

  if (value < 60) {
    return `${value} 秒`;
  }

  const minutes = Math.floor(value / 60);
  const seconds = value % 60;
  return seconds === 0 ? `${minutes} 分钟` : `${minutes} 分 ${seconds} 秒`;
}

export function sortSourceHealth(items: SourceHealth[]): SourceHealth[] {
  const weight: Record<SourceHealth['health_status'], number> = {
    failed: 0,
    warning: 1,
    never: 2,
    healthy: 3,
    disabled: 4,
  };

  return [...items].sort((left, right) => {
    const healthDifference =
      weight[left.health_status] - weight[right.health_status];

    if (healthDifference !== 0) {
      return healthDifference;
    }

    return (
      (diagnosisWeight[left.diagnosis_code] ?? 99) -
      (diagnosisWeight[right.diagnosis_code] ?? 99)
    );
  });
}

export function getLatestRun(source: SourceHealth) {
  return source.recent_crawl_runs[0] ?? null;
}

export function getSaveRate(
  run: SourceHealth['recent_crawl_runs'][number]
): number {
  if (run.found_count <= 0) {
    return 0;
  }

  return Math.round((run.saved_count / run.found_count) * 100);
}

export function getSourceReviewReason(source: SourceHealth): string | null {
  const latestRun = getLatestRun(source);

  if (source.rollout_stage === 'blocked') {
    return '来源入口阻塞';
  }

  if (source.rollout_stage === 'discovery_only') {
    return '仅发现待确认';
  }

  if (source.rollout_stage === 'standard_review') {
    return '待小样本复核';
  }

  if (!source.think_tank_is_verified) {
    return '机构信息待校对';
  }

  if (source.health_status === 'failed') {
    return '最近抓取失败';
  }

  if (source.health_status === 'never') {
    return '尚未试抓';
  }

  if (latestRun && latestRun.found_count > 0 && latestRun.saved_count === 0) {
    return source.diagnosis_label || '有候选但未入库';
  }

  if (
    source.health_status === 'healthy' &&
    source.report_count === 0 &&
    !['ok', 'unknown'].includes(source.diagnosis_code)
  ) {
    return source.diagnosis_label;
  }

  if (latestRun && latestRun.status === 'running') {
    return '抓取仍在运行';
  }

  return null;
}
