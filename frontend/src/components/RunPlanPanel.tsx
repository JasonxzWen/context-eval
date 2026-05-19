import type { EditableAgent, EditableVariant, RunPlan } from '../types';

type RunPlanPanelProps = {
  agents: EditableAgent[];
  taskCount: number;
  variants: EditableVariant[];
  visibleCaseCount: number;
  plan: RunPlan | null;
  defaultTrials: number;
};

export function RunPlanPanel({
  agents,
  taskCount,
  variants,
  visibleCaseCount,
  plan,
  defaultTrials,
}: RunPlanPanelProps) {
  return (
    <section className="panel matrix-panel">
      <div className="panel-heading">
        <h2>Run Plan</h2>
        <span data-testid="matrix-count">{visibleCaseCount}</span>
      </div>
      <dl className="metric-grid">
        <div>
          <dt>agents</dt>
          <dd>{agents.length}</dd>
        </div>
        <div>
          <dt>tasks</dt>
          <dd>{taskCount}</dd>
        </div>
        <div>
          <dt>variants</dt>
          <dd>{variants.length}</dd>
        </div>
        <div>
          <dt>trials</dt>
          <dd>{plan?.trials ?? defaultTrials}</dd>
        </div>
      </dl>
      <ul className="check-list">
        {(plan?.cases || []).slice(0, 4).map((caseItem) => (
          <li key={caseItem.case_id}>
            <strong>{caseItem.case_id}</strong>
            <span>{caseItem.expected_outcome_summary || '无 expected_outcome summary'}</span>
            <small>
              {caseItem.hard_evaluation_enabled ? 'hard on' : 'hard off'} /{' '}
              {caseItem.soft_evaluation_enabled ? 'soft on' : 'soft off'}
            </small>
          </li>
        ))}
      </ul>
      {!plan && (
        <p className="panel-note">保存任务或点击“开始运行”后会刷新具体 case，并在失败时显示配置或执行错误。</p>
      )}
    </section>
  );
}
