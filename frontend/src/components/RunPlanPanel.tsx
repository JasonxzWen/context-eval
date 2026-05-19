import type { EditableAgent, EditableVariant, RunPlan, RunScope } from '../types';

type RunPlanPanelProps = {
  agents: EditableAgent[];
  taskCount: number;
  variants: EditableVariant[];
  visibleCaseCount: number;
  plan: RunPlan | null;
  defaultTrials: number;
  runScope: RunScope;
};

export function RunPlanPanel({
  agents,
  taskCount,
  variants,
  visibleCaseCount,
  plan,
  defaultTrials,
  runScope,
}: RunPlanPanelProps) {
  return (
    <section className="panel matrix-panel">
      <div className="panel-heading">
        <h2>执行计划</h2>
        <span data-testid="matrix-count">{visibleCaseCount}</span>
      </div>
      <dl className="metric-grid">
        <div>
          <dt>执行器</dt>
          <dd>{runScope.agents.length || agents.length}</dd>
        </div>
        <div>
          <dt>任务</dt>
          <dd>{runScope.task_ids.length || taskCount}</dd>
        </div>
        <div>
          <dt>上下文版本</dt>
          <dd>{runScope.variants.length || variants.length}</dd>
        </div>
        <div>
          <dt>轮次</dt>
          <dd>{plan?.trials ?? defaultTrials}</dd>
        </div>
      </dl>
      <p className="panel-note">
        预计用例数 = 任务 × 上下文版本 × 执行器 × 轮次。这里用于确认本次会花多少执行成本。
      </p>
      <ul className="check-list">
        {(plan?.cases || []).slice(0, 4).map((caseItem) => (
          <li key={caseItem.case_id}>
            <strong>{caseItem.case_id}</strong>
            <span>{caseItem.expected_outcome_summary || '未配置期望结果摘要'}</span>
            <small>
              {caseItem.hard_evaluation_enabled ? '硬性检查开启' : '硬性检查关闭'} /{' '}
              {caseItem.soft_evaluation_enabled ? '人工评审规则已配置' : '未配置人工评审规则'}
            </small>
          </li>
        ))}
      </ul>
      {!plan && (
        <p className="panel-note">保存配置或点击“刷新执行计划”后会列出具体评测用例。</p>
      )}
    </section>
  );
}
