'use client';

export function SettingsWorkbenchIntro() {
  return (
    <section className="settings-workbench-intro" aria-label="来源治理流程">
      <div>
        <strong>1. 覆盖重点机构</strong>
        <span>先补齐 P0/P1 智库来源，保证美国核心机构稳定监测。</span>
      </div>
      <div>
        <strong>2. 验收候选质量</strong>
        <span>查看候选报告、跳过原因和保存率，判断来源是否可放行。</span>
      </div>
      <div>
        <strong>3. 小批量试运行</strong>
        <span>只让通过复核的来源进入自动入库，异常来源先停留在人工确认。</span>
      </div>
    </section>
  );
}
