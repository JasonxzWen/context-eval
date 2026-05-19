import type { EditableAgent, EditableTask, EditableVariant, ResultsPayload, RunPlan, RunScope } from '../types';

type RunControlsProps = {
  cleanupPolicy: string;
  isRunActive: boolean;
  plan: RunPlan | null;
  preflightChecks: string[];
  preflightStatus: string;
  resultSummary: { validationFailed: number; hardFailed: number } | null;
  results: ResultsPayload | null;
  runBrief: string;
  runScope: RunScope;
  selectedCaseCount: number;
  serverMode: 'checking' | 'connected' | 'fixture';
  taskSummary: string;
  taskTitle: string;
  tasks: EditableTask[];
  variants: EditableVariant[];
  agents: EditableAgent[];
  onCleanupPolicyChange: (policy: string) => void;
  onPlan: () => void;
  onRevealResults: () => void;
  onStart: () => void;
  onStop: () => void;
  onToggleScope: (kind: keyof RunScope, value: string, checked: boolean) => void;
  labelForCheck: (check: string) => string;
};

export function RunControls({
  cleanupPolicy,
  isRunActive,
  plan,
  preflightChecks,
  preflightStatus,
  resultSummary,
  results,
  runBrief,
  runScope,
  selectedCaseCount,
  serverMode,
  taskSummary,
  taskTitle,
  tasks,
  variants,
  agents,
  onCleanupPolicyChange,
  onPlan,
  onRevealResults,
  onStart,
  onStop,
  onToggleScope,
  labelForCheck,
}: RunControlsProps) {
  const canRun =
    serverMode === 'connected' &&
    !isRunActive &&
    runScope.task_ids.length > 0 &&
    runScope.variants.length > 0 &&
    runScope.agents.length > 0;
  const plannedCount = plan?.case_count ?? selectedCaseCount;

  return (
    <section className="panel run-brief-panel">
      <div className="panel-heading">
        <h2>本次运行</h2>
        <span>{results ? '已出结果' : isRunActive ? '运行中' : '待运行'}</span>
      </div>
      <div className="brief-layout">
        <div className="brief-copy">
          <strong>{taskTitle}</strong>
          <span>{taskSummary}</span>
          <p>{runBrief}</p>
        </div>
        <fieldset className="scope-panel">
          <legend>运行范围</legend>
          <ScopeGroup
            title="任务"
            emptyLabel="未配置任务"
            values={tasks.map((task) => task.id).filter(Boolean)}
            selected={runScope.task_ids}
            labelPrefix="任务"
            onToggle={(value, checked) => onToggleScope('task_ids', value, checked)}
          />
          <ScopeGroup
            title="上下文版本"
            emptyLabel="未配置上下文版本"
            values={variants.map((variant) => variant.name).filter(Boolean)}
            selected={runScope.variants}
            labelPrefix="上下文版本"
            onToggle={(value, checked) => onToggleScope('variants', value, checked)}
          />
          <ScopeGroup
            title="执行器"
            emptyLabel="未配置执行器"
            values={agents.map((agent) => agent.name).filter(Boolean)}
            selected={runScope.agents}
            labelPrefix="执行器"
            onToggle={(value, checked) => onToggleScope('agents', value, checked)}
          />
        </fieldset>
        <div className="brief-actions">
          <label htmlFor="cleanup-policy">
            清理策略
            <select
              id="cleanup-policy"
              value={cleanupPolicy}
              onChange={(event) => onCleanupPolicyChange(event.target.value)}
            >
              <option value="never">保留所有工作区</option>
              <option value="always">总是清理</option>
              <option value="successful">成功后清理</option>
              <option value="failed">失败后清理</option>
            </select>
          </label>
          <div className="button-row">
            <button type="button" className="secondary" onClick={onPlan} disabled={!canRun}>
              刷新执行计划
            </button>
            <button type="button" onClick={onStart} disabled={!canRun}>
              {isRunActive ? '运行中' : '开始运行'}
            </button>
            <button type="button" className="secondary" onClick={onStop} disabled={!isRunActive}>
              停止
            </button>
          </div>
        </div>
      </div>
      <dl className="run-prep-summary">
        <div>
          <dt>配置检查</dt>
          <dd data-testid="preflight-status">{preflightStatus}</dd>
        </div>
        <div>
          <dt>当前选择</dt>
          <dd>
            {runScope.task_ids.length} 个任务 / {runScope.variants.length} 个上下文版本 /{' '}
            {runScope.agents.length} 个执行器
          </dd>
        </div>
        <div>
          <dt>预计用例</dt>
          <dd>
            <strong data-testid="planned-case-count">{plannedCount}</strong>
            {!plan && plannedCount > 0 && <small>预计</small>}
          </dd>
        </div>
      </dl>
      {preflightChecks.length > 0 && (
        <details className="prep-details">
          <summary>已通过 {preflightChecks.length} 项运行前检查</summary>
          <ul className="inline-check-list">
            {preflightChecks.map((check) => (
              <li key={check}>{labelForCheck(check)}</li>
            ))}
          </ul>
        </details>
      )}
      {results && (
        <div className="result-callout" role="status">
          <div>
            <strong>结果已生成</strong>
            <span>
              {results.overview.case_count} 个用例，验证失败{' '}
              {resultSummary?.validationFailed ?? 0}，硬性检查失败{' '}
              {resultSummary?.hardFailed ?? 0}，遥测缺口{' '}
              {results.overview.telemetry_gap_count}
            </span>
          </div>
          <button type="button" className="secondary" onClick={onRevealResults}>
            查看结果
          </button>
        </div>
      )}
    </section>
  );
}

type ScopeGroupProps = {
  title: string;
  emptyLabel: string;
  values: string[];
  selected: string[];
  labelPrefix: string;
  onToggle: (value: string, checked: boolean) => void;
};

function ScopeGroup({
  title,
  emptyLabel,
  values,
  selected,
  labelPrefix,
  onToggle,
}: ScopeGroupProps) {
  return (
    <div className="scope-group">
      <strong>{title}</strong>
      <div className="scope-options">
        {values.map((value) => (
          <label key={value} className="scope-option">
            <input
              type="checkbox"
              aria-label={`${labelPrefix} ${value}`}
              checked={selected.includes(value)}
              onChange={(event) => onToggle(value, event.target.checked)}
            />
            <span>{value}</span>
          </label>
        ))}
        {values.length === 0 && <span className="status-line">{emptyLabel}</span>}
      </div>
    </div>
  );
}
