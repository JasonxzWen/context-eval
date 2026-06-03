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
    <section className="panel matrix-panel" id="run-plan">
      <div className="panel-heading">
        <h2>评测计划</h2>
        <span data-testid="matrix-count">{visibleCaseCount}</span>
      </div>
      <dl className="metric-grid">
        <div>
          <dt>本地 AI</dt>
          <dd>{runScope.agents.length || agents.length}</dd>
        </div>
        <div>
          <dt>评测题目</dt>
          <dd>{runScope.task_ids.length || taskCount}</dd>
        </div>
        <div>
          <dt>对比资料</dt>
          <dd>{runScope.variants.length || variants.length}</dd>
        </div>
        <div>
          <dt>轮次</dt>
          <dd>{plan?.trials ?? defaultTrials}</dd>
        </div>
      </dl>
      <p className="panel-note">
        预计结果数 = 评测题目 × 对比资料 × 本地 AI × 轮次。
      </p>
      <ul className="check-list">
        {(plan?.cases || []).slice(0, 4).map((caseItem) => (
          <li key={caseItem.case_id}>
            <strong>{caseItem.case_id}</strong>
            <span>{caseItem.expected_outcome_summary || '未配置验收 / 仲裁目标'}</span>
            <small>
              {caseItem.case_type ? `类型 ${formatCaseType(caseItem.case_type)} / ` : ''}
              {caseItem.reference_evidence_summary ? '真实对照已填写 / ' : ''}
              {caseItem.hard_evaluation_enabled ? '硬性检查开启' : '硬性检查关闭'} /{' '}
              {caseItem.soft_evaluation_enabled
                ? `AI 仲裁：${caseItem.soft_evaluation_runner_agent || '同评测用的本地 AI'}`
                : 'AI 仲裁关闭'}
            </small>
          </li>
        ))}
      </ul>
      {!plan && (
        <p className="panel-note">保存配置或点击“刷新评测计划”后会列出具体评测结果。</p>
      )}
    </section>
  );
}
