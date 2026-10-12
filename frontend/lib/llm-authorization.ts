import { apiRequest } from '@/lib/api';

export type LLMAuthorizationScope = 'relevance_sample' | 'report_generation';

export type LLMAuthorizationPreview = {
  scope: LLMAuthorizationScope;
  target_id: number;
  title: string;
  document_hash: string;
  content_length: number;
  data_scope: string;
  provider: string;
  endpoint: string;
  model: string;
  policy_version: number;
  outbound_enabled: boolean;
  authorized: boolean;
};

export type LLMAuthorization = {
  id: number;
  scope: LLMAuthorizationScope;
  target_key: string;
  document_hash: string;
  policy_version: number;
  provider: string;
  endpoint: string;
  model: string;
  candidate_id: number | null;
  report_id: number | null;
  granted_by: number | null;
  granted_at: string;
  revoked_by: number | null;
  revoked_at: string | null;
};

function targetQuery(scope: LLMAuthorizationScope, targetId: number): string {
  const query = new URLSearchParams({
    scope,
    target_id: String(targetId),
  });
  return query.toString();
}

export function fetchLLMAuthorizationPreview(
  scope: LLMAuthorizationScope,
  targetId: number
): Promise<LLMAuthorizationPreview> {
  return apiRequest<LLMAuthorizationPreview>(`/api/v1/llm-authorizations/preview?${targetQuery(scope, targetId)}`);
}

export function fetchLLMAuthorizationHistory(
  scope: LLMAuthorizationScope,
  targetId: number
): Promise<LLMAuthorization[]> {
  return apiRequest<LLMAuthorization[]>(`/api/v1/llm-authorizations?${targetQuery(scope, targetId)}`);
}

export function grantLLMAuthorization(preview: LLMAuthorizationPreview): Promise<LLMAuthorization> {
  return apiRequest<LLMAuthorization>('/api/v1/llm-authorizations', {
    method: 'POST',
    body: JSON.stringify({
      scope: preview.scope,
      target_id: preview.target_id,
      document_hash: preview.document_hash,
      provider: preview.provider,
      endpoint: preview.endpoint,
      model: preview.model,
      policy_version: preview.policy_version,
      consent: 'allow_external_processing',
    }),
  });
}

export function revokeLLMAuthorization(
  scope: LLMAuthorizationScope,
  targetId: number
): Promise<{ revoked_count: number }> {
  return apiRequest<{ revoked_count: number }>(`/api/v1/llm-authorizations/revoke?${targetQuery(scope, targetId)}`, {
    method: 'POST',
  });
}
