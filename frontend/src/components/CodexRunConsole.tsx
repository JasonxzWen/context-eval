import type {
  CodexProfileDiagnostic,
  EditableAgent,
  EnvironmentPayload,
  ResultsPayload,
  RunPlan,
  RunScope,
} from '../types';

type CodexRunConsoleProps = {
  agents: EditableAgent[];
  configLoaded: boolean;
  diagnostics: CodexProfileDiagnostic[];
  environment: EnvironmentPayload | null;
  environmentStatus: string;
  isRunActive: boolean;
  plan: RunPlan | null;
  preflightStatus: string;
  projectPath: string;
  results: ResultsPayload | null;
  runLabel: string;
  runScope: RunScope;
  visibleCaseCount: number;
};

function hasCommandPart(agent: EditableAgent | undefined, part: string) {
  return Boolean(agent?.command.toLowerCase().includes(part));
}

function selectedAgent(agents: EditableAgent[], runScope: RunScope) {
  const selected = agents.filter((agent) => runScope.agents.includes(agent.name));
  return (
    selected.find((agent) => agent.kind === 'codex-cli')
    || agents.find((agent) => agent.kind === 'codex-cli')
    || selected[0]
    || agents[0]
  );
}

function statusText(ok: boolean) {
  return ok ? '已就绪' : '需处理';
}

function nextActionLabel({
  agent,
  configLoaded,
  diagnostics,
  isRunActive,
  plan,
  results,
}: {
  agent: EditableAgent | undefined;
  configLoaded: boolean;
  diagnostics: CodexProfileDiagnostic[];
  isRunActive: boolean;
  plan: RunPlan | null;
  results: ResultsPayload | null;
}) {
  if (!configLoaded) return '先打开项目';
  if (!agent) return '配置 Codex profile';
  if (agent.kind !== 'codex-cli') return '切换到 Codex CLI';
  if (diagnostics.length > 0) return '修复可观测性';
  if (isRunActive) return '等待运行完成';
  if (results) return '查看结果证据';
  if (!plan) return '刷新评测计划';
  return '可以开始评测';
}

export function CodexRunConsole({
  agents,
  configLoaded,
  diagnostics,
  environment,
  environmentStatus,
  isRunActive,
  plan,
  preflightStatus,
  projectPath,
  results,
  runLabel,
  runScope,
  visibleCaseCount,
}: CodexRunConsoleProps) {
  const agent = selectedAgent(agents, runScope);
  const isCodex = agent?.kind === 'codex-cli';
  const hasCodexExec = hasCommandPart(agent, 'codex exec');
  const hasJson = hasCommandPart(agent, '--json');
  const hasFinalMessage = hasCommandPart(agent, '--output-last-message');
  const hasCodexJsonl = agent?.telemetry?.collector === 'codex-jsonl';
  const scopedDiagnostics = diagnostics.filter(
    (diagnostic) => !agent || diagnostic.agent_name === agent.name,
  );
  const nextAction = nextActionLabel({
    agent,
    configLoaded,
    diagnostics: scopedDiagnostics,
    isRunActive,
    plan,
    results,
  });

  return (
    <section className="panel codex-console-panel" id="run-console" data-testid="codex-run-console">
      <div className="panel-heading">
        <h2>Codex-first 运行台</h2>
        <span data-testid="codex-next-action">{nextAction}</span>
      </div>

      <div className="codex-console-grid">
        <article className="console-card">
          <span>项目</span>
          <strong>{projectPath || '未打开项目'}</strong>
          <small>{environmentStatus || environment?.repo?.branch || '本机状态未检查'}</small>
        </article>

        <article className="console-card">
          <span>Codex profile</span>
          <strong>{agent?.name || '未配置'}</strong>
          <small>{isCodex ? 'Codex CLI' : agent ? `当前是 ${agent.kind}` : '需要添加执行器'}</small>
        </article>

        <article className="console-card">
          <span>可观测性</span>
          <strong>{hasCodexJsonl ? 'codex-jsonl' : agent?.telemetry?.collector || 'none'}</strong>
          <small>{scopedDiagnostics.length > 0 ? `${scopedDiagnostics.length} 个提醒` : preflightStatus}</small>
        </article>

        <article className="console-card">
          <span>运行计划</span>
          <strong>{plan?.case_count ?? visibleCaseCount}</strong>
          <small>{runLabel}</small>
        </article>
      </div>

      <div className="codex-readiness-grid" aria-label="Codex profile readiness">
        <div className={isCodex ? 'ready' : 'warn'}>
          <strong>{statusText(isCodex)}</strong>
          <span>profile 类型</span>
        </div>
        <div className={hasCodexExec ? 'ready' : 'warn'}>
          <strong>{statusText(hasCodexExec)}</strong>
          <span>codex exec</span>
        </div>
        <div className={hasJson ? 'ready' : 'warn'}>
          <strong>{statusText(hasJson)}</strong>
          <span>--json</span>
        </div>
        <div className={hasFinalMessage ? 'ready' : 'warn'}>
          <strong>{statusText(hasFinalMessage)}</strong>
          <span>final message</span>
        </div>
        <div className={hasCodexJsonl ? 'ready' : 'warn'}>
          <strong>{statusText(hasCodexJsonl)}</strong>
          <span>telemetry</span>
        </div>
      </div>

      {scopedDiagnostics.length > 0 ? (
        <ul className="codex-diagnostic-list" data-testid="codex-diagnostics">
          {scopedDiagnostics.map((diagnostic) => (
            <li key={`${diagnostic.agent_name}:${diagnostic.code}`}>
              <strong>{diagnostic.message}</strong>
              <span>{diagnostic.next_step}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="status-line" data-testid="codex-diagnostics">
          Codex profile 已具备结构化运行证据入口。
        </p>
      )}
    </section>
  );
}
