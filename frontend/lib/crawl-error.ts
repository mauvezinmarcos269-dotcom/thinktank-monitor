const crawlErrorSummaryMaxLength = 180;

function truncateCrawlErrorSummary(text: string): string {
  if (text.length <= crawlErrorSummaryMaxLength) {
    return text;
  }

  return `${text.slice(0, crawlErrorSummaryMaxLength - 1).trimEnd()}…`;
}

export function summarizeCrawlError(text: string | null): string {
  if (!text?.trim()) {
    return '无';
  }

  const compact = text.replace(/\s+/g, ' ').trim();
  const sqlDetailsIndex = compact.search(/\s+\[(?:SQL|parameters):/i);
  const summarySource = sqlDetailsIndex >= 0 ? compact.slice(0, sqlDetailsIndex).trimEnd() : compact;

  const undefinedColumn = summarySource.match(
    /UndefinedColumnError.*?column ["']([^"']+)["'] of relation ["']([^"']+)["']/i
  );
  if (undefinedColumn) {
    return `数据库结构未同步：数据表 ${undefinedColumn[2]} 缺少字段 ${undefinedColumn[1]}。`;
  }

  const httpStatus = summarySource.match(/HTTPStatusError:.*?["'](\d{3})\s+[^"']+["']/i);
  if (httpStatus) {
    return `来源访问失败：目标网站返回 HTTP ${httpStatus[1]}。`;
  }

  if (/所有发现入口抓取失败/i.test(summarySource)) {
    return '来源连接失败：所有发现入口均无法访问。';
  }

  if (/ConnectError:/i.test(summarySource)) {
    return '来源连接失败：无法连接目标网站。';
  }

  if (/TimeoutError:/i.test(summarySource)) {
    return '来源访问超时：目标网站未在限定时间内响应。';
  }

  if (/RSS 解析失败/i.test(summarySource)) {
    if (/undefined entity/i.test(summarySource)) {
      return 'RSS 解析失败：订阅内容包含无法识别的格式。';
    }

    const rssReason = summarySource.match(/RSS 解析失败[:：]\s*(.+)$/i)?.[1];
    return truncateCrawlErrorSummary(rssReason ? `RSS 解析失败：${rssReason}` : 'RSS 解析失败：订阅内容无法读取。');
  }

  const missingParser = summarySource.match(/当前尚未配置该\s+website\s+来源的专用解析器[:：]\s*(\S+)/i);
  if (missingParser) {
    return `来源尚未适配：未配置该网站的专用解析器（${missingParser[1]}）。`;
  }

  if (/ProgrammingError:/i.test(summarySource)) {
    return '数据库操作失败：请展开查看具体数据库异常。';
  }

  if (/IntegrityError:/i.test(summarySource)) {
    return '数据库写入失败：数据约束校验未通过。';
  }

  if (/OperationalError:/i.test(summarySource)) {
    return '数据库连接或执行失败：请检查数据库服务。';
  }

  const localizedValueError = summarySource.match(/^ValueError:\s*([\u3400-\u9fff].*)$/);
  if (localizedValueError) {
    return truncateCrawlErrorSummary(localizedValueError[1]);
  }

  return truncateCrawlErrorSummary(summarySource);
}

export function formatDailySummaryMessage(message: string): string {
  let inFailureSection = false;
  const formattedLines: string[] = [];

  for (const line of message.split('\n')) {
    if (line.trim() === '最近失败原因：') {
      inFailureSection = true;
      formattedLines.push(line);
      continue;
    }

    if (!inFailureSection) {
      formattedLines.push(line);
      continue;
    }

    if (line.startsWith('- ')) {
      const separatorIndex = line.indexOf('：', 2);
      if (separatorIndex < 0) {
        formattedLines.push(line);
        continue;
      }

      const prefix = line.slice(0, separatorIndex + 1);
      const error = line.slice(separatorIndex + 1).trim();
      formattedLines.push(`${prefix}${summarizeCrawlError(error)}`);
      continue;
    }

    if (!line.trim()) {
      formattedLines.push(line);
    }
  }

  return formattedLines.join('\n');
}
