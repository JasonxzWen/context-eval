import type { ResultsPayload, RunStatus } from '../types';
import { RunScoreSummary } from './RunScoreSummary';

export type OnboardingHomeState = 'empty' | 'ready' | 'running' | 'completed' | 'failed';

type OnboardingHomeProps = {
  state: OnboardingHomeState;
  run: RunStatus | null;
  results: ResultsPayload | null;
  runBrief: string;
  visibleCaseCount: number;
  primaryDisabled?: boolean;
  onPrimaryAction: () => void;
  onOpenProject: () => void;
  onAdvancedWorkbench: () => void;
  onViewEvidence: () => void;
};

function stateLabel(state: OnboardingHomeState) {
  if (state === 'empty') return '未配置';
  if (state === 'ready') return '可运行';
  if (state === 'running') return '运行中';
  if (state === 'completed') return '已完成';
  return '失败';
}

function primaryLabel(state: OnboardingHomeState) {
  if (state === 'empty') return '运行一次 demo 评测';
  if (state === 'ready') return '运行一次评测';
  if (state === 'failed') return '重新运行';
  return '运行中';
}

export function OnboardingHome({
  state,
  run,
  results,
  runBrief,
  visibleCaseCount,
  primaryDisabled = false,
  onPrimaryAction,
  onOpenProject,
  onAdvancedWorkbench,
  onViewEvidence,
}: OnboardingHomeProps) {
  const completed = run?.completed_cases ?? 0;
  const total = run?.case_count || visibleCaseCount || 0;
  const progress = total > 0 ? Math.min(100, Math.round((completed / total) * 100)) : 0;

  return (
    <section className="onboarding-home" data-testid="onboarding-home" aria-label="运行向导">
      <div className="onboarding-status">
        <span>当前状态</span>
        <strong>{stateLabel(state)}</strong>
      </div>
      <div className="onboarding-copy">
        <p className="eyebrow">context-eval onboarding</p>
        <h2>先跑通一次评测</h2>
        <p>{runBrief}</p>
      </div>

      {state === 'running' && (
        <div className="onboarding-progress" role="status">
          <div>
            <strong>
              {completed}/{total || '-'}
            </strong>
            <span>{progress}%</span>
          </div>
          <progress value={progress} max={100} />
        </div>
      )}

      {state === 'completed' && results ? (
        <RunScoreSummary results={results} onViewEvidence={onViewEvidence} />
      ) : (
        <div className="onboarding-actions">
          <button
            type="button"
            className="onboarding-primary"
            onClick={onPrimaryAction}
            disabled={primaryDisabled || state === 'running'}
          >
            {primaryLabel(state)}
          </button>
        </div>
      )}

      <div className="onboarding-secondary-actions">
        <button type="button" className="link-button" onClick={onOpenProject}>
          我已经有项目
        </button>
        <button type="button" className="link-button" onClick={onAdvancedWorkbench}>
          高级工作台
        </button>
        {results && state !== 'completed' && (
          <button type="button" className="link-button" onClick={onViewEvidence}>
            查看完整证据
          </button>
        )}
      </div>
    </section>
  );
}
