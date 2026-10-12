const reportErrorSummaryMaxLength = 180;

export type ReportProcessingOperation = 'ai' | 'fetch';

const aiFieldLabels: Record<string, string> = {
  translation: '翻译稿',
  summary: '摘要稿',
  commentary: '评论稿',
};

function truncateReportError(text: string): string {
  if (text.length <= reportErrorSummaryMaxLength) {
    return text;
  }

  return `${text.slice(0, reportErrorSummaryMaxLength - 1).trimEnd()}…`;
}

function stripExceptionPrefixes(text: string): string {
  const prefixes = [
    '报告最终摘要/评论生成失败:',
    '报告最终摘要/评论生成失败：',
    '全文翻译生成失败:',
    '全文翻译生成失败：',
    '全文摘要生成失败:',
    '全文摘要生成失败：',
    '全文评论生成失败:',
    '全文评论生成失败：',
    'ValueError:',
    'RuntimeError:',
    'ReportDocumentValidationError:',
  ];
  let current = text.trim();
  let changed = true;

  while (changed) {
    changed = false;
    const prefix = prefixes.find((item) => current.startsWith(item));
    if (prefix) {
      current = current.slice(prefix.length).trim();
      changed = true;
    }
  }

  return current;
}

export function summarizeReportProcessingError(text: string | null, operation: ReportProcessingOperation): string {
  if (!text?.trim()) {
    return '未记录具体失败原因。';
  }

  const compact = text.replace(/\s+/g, ' ').trim();
  const sqlDetailsIndex = compact.search(/\s+\[(?:SQL|parameters):/i);
  const summarySource = sqlDetailsIndex >= 0 ? compact.slice(0, sqlDetailsIndex).trimEnd() : compact;
  const lengthError = summarySource.match(
    /\b(translation|summary|commentary)\s+长度(不足|超出):\s*期望(至少|不超过)\s*(\d+)\s*字符，实际为\s*(\d+)\s*字符/i
  );

  if (operation === 'ai' && lengthError) {
    const [, field, status, expectation, expected, actual] = lengthError;
    return `AI ${aiFieldLabels[field.toLowerCase()]}长度${status}：要求${expectation} ${expected} 字，实际 ${actual} 字。`;
  }

  const httpStatus = summarySource.match(/(?:HTTPStatusError:\s*)?(?:Client|Server) error ["'](\d{3})\s+[^"']+["']/i);
  if (httpStatus) {
    const subject = operation === 'ai' ? 'AI 服务' : '报告正文地址';
    return `${subject}请求失败：返回 HTTP ${httpStatus[1]}。`;
  }

  if (/Timeout(?:Exception|Error)|ReadTimeout|ConnectTimeout/i.test(summarySource)) {
    return operation === 'ai' ? 'AI 服务响应超时，请稍后重试。' : '报告正文获取超时，请稍后重试。';
  }

  if (/ConnectError|ConnectException/i.test(summarySource)) {
    return operation === 'ai' ? '无法连接 AI 服务，请检查服务配置和网络。' : '无法连接报告正文地址。';
  }

  if (operation === 'ai') {
    if (summarySource.includes('LLM_API_KEY 未配置')) return 'AI 服务配置不完整：缺少 API 密钥。';
    if (summarySource.includes('LLM_BASE_URL 未配置')) return 'AI 服务配置不完整：缺少服务地址。';
    if (summarySource.includes('LLM_MODEL 未配置')) return 'AI 服务配置不完整：缺少模型名称。';
    if (summarySource.includes('外发总开关已关闭')) return 'AI 处理未执行：外发总开关已关闭。';
    if (summarySource.includes('未授权') || summarySource.includes('缺少授权')) {
      return 'AI 处理未执行：当前文档尚未获得相应用途授权。';
    }
    if (summarySource.includes('不是有效 JSON') || summarySource.includes('返回格式异常')) {
      return 'AI 返回格式异常：未获得有效的结构化内容。';
    }
    if (summarySource.includes('LLM 返回为空') || summarySource.includes('最终摘要不能为空')) {
      return 'AI 未返回有效摘要内容。';
    }
    if (summarySource.includes('最终评论不能为空')) return 'AI 未返回有效评论内容。';
    if (summarySource.includes('最终翻译不能为空')) return 'AI 未返回有效翻译内容。';
  }

  const stripped = stripExceptionPrefixes(summarySource);
  if (stripped) {
    return truncateReportError(stripped);
  }

  return operation === 'ai' ? 'AI 处理失败，请查看任务日志。' : '报告正文获取失败，请查看任务日志。';
}

function formatAlreadyStructuredMessage(message: string, operation: ReportProcessingOperation): string | null {
  const separator = '\n\n失败原因：';
  const separatorIndex = message.indexOf(separator);
  if (separatorIndex < 0) {
    return null;
  }

  const title = message.slice(0, separatorIndex);
  const error = message.slice(separatorIndex + separator.length);
  return `${title}${separator}${summarizeReportProcessingError(error, operation)}`;
}

export function formatReportFailureNotification(eventType: string, message: string): string {
  const operation: ReportProcessingOperation | null =
    eventType === 'report.ai_failed' ? 'ai' : eventType === 'report.fetch_failed' ? 'fetch' : null;
  if (!operation) {
    return message;
  }

  const structured = formatAlreadyStructuredMessage(message, operation);
  if (structured) {
    return structured;
  }

  if (operation === 'ai') {
    const marker = ': 报告最终摘要/评论生成失败:';
    const markerIndex = message.lastIndexOf(marker);
    if (markerIndex >= 0) {
      const title = message.slice(0, markerIndex);
      const error = message.slice(markerIndex + 2);
      return `${title}\n\n失败原因：${summarizeReportProcessingError(error, operation)}`;
    }
  }

  const technicalMarkers = [
    ': ValueError:',
    ': RuntimeError:',
    ': ReportDocumentValidationError:',
    ': HTTPStatusError:',
    ': TimeoutError:',
    ': ConnectError:',
  ];
  const marker = technicalMarkers
    .map((value) => ({ value, index: message.lastIndexOf(value) }))
    .filter(({ index }) => index >= 0)
    .sort((left, right) => right.index - left.index)[0];

  if (!marker) {
    return message;
  }

  const title = message.slice(0, marker.index);
  const error = message.slice(marker.index + 2);
  return `${title}\n\n失败原因：${summarizeReportProcessingError(error, operation)}`;
}
