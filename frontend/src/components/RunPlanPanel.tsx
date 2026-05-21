import type { EditableAgent, EditableVariant, RunPlan, RunScope } from '../types';
import { formatCaseType } from '../caseTypes';

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
          <dt>测试用例</dt>
          <dd>{runScope.task_ids.length || taskCount}</dd>
        </div>
        <div>
          <dt>资料包</dt>
          <dd>{runScope.variants.length || variants.length}</dd>
        </div>
        <div>
          <dt>轮次</dt>
          <dd>{plan?.trials ?? defaultTrials}</dd>
        </div>
      </dl>
      <p className="panel-note">
        预计用例数 = 测试用例 × 资料包 × 执行器 × 轮次。
      </p>
      <ul className="check-list">
        {(plan?.cases || []).slice(0, 4).map((caseItem) => (
          <li key={caseItem.case_id}>
            <strong>{caseItem.case_id}</strong>
            <span>{caseItem.expected_outcome_summary || '未配置验收 / 仲裁目标'}</span>
            <small>
              {caseItem.case_type ? `类型 ${formatCaseType(caseItem.case_type)} / ` : ''}
              {caseItem.reference_evidence_summary ? '参考答案已填写 / ' : ''}
              {caseItem.hard_evaluation_enabled ? '硬性检查开启' : '硬性检查关闭'} /{' '}
              {caseItem.soft_evaluation_enabled
                ? (caseItem.soft_evaluation_mode === 'runner'
                    ? `AI 仲裁执行器 ${caseItem.soft_evaluation_runner_agent || '同评测执行器'}`
                    : 'AI 仲裁材料已配置')
                : '未配置 AI 仲裁维度'}
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
