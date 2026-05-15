import { useEffect, useMemo, useState } from 'react';
import { localAppFixture, plannedCaseCount } from './fixture';
import './styles.css';

type EditableAgent = {
  name: string;
  kind: string;
  command: string;
  timeout_minutes: number;
  network: string;
};

type SnippetCheck = {
  path: string;
  snippets: string[];
};

type ExpectedOutcome = {
  summary?: string | null;
  forbidden_paths?: string[];
  acceptance_points?: string[];
  files?: {
    path: string;
    change_type?: string;
    must_change?: boolean;
    expected_snippets?: string[];
    forbidden_snippets?: string[];
  }[];
};

type HardEvaluation = {
  enabled: boolean;
  require_validation_pass?: boolean;
  max_changed_files?: number | null;
  required_paths?: string[];
  forbidden_paths?: string[];
  expected_snippets?: SnippetCheck[];
  forbidden_snippets?: SnippetCheck[];
};

type SoftEvaluation = {
  enabled: boolean;
  mode: 'payload-only';
  max_score?: number;
  rubric?: { name: string; weight: number; description: string }[];
};

type EditableTask = {
  id: string;
  title?: string | null;
  prompt: string;
  category?: string | null;
  difficulty?: string | null;
  repo_ref?: string | null;
  validation_commands: string[];
  expected_outcome?: ExpectedOutcome | null;
  hard_evaluation?: HardEvaluation | null;
  soft_evaluation?: SoftEvaluation | null;
};

type EditableVariant = {
  name: string;
  description: string;
  overlays: { source: string; target: string }[];
};

type LoadedConfig = {
  config_path: string;
  tasks_path: string;
  config_yaml: string;
  tasks_yaml: string;
  editable: {
    repo: { path: string; base_ref: string };
    agent: EditableAgent;
    agent_shape: string;
    agents: EditableAgent[];
    tasks_path: string;
    variants: EditableVariant[];
    tasks: EditableTask[];
    evaluation_commands: string[];
    evaluation_timeout_seconds?: number | null;
    output_dir?: string | null;
  };
  resolved: {
    repo_path: string;
    output_dir: string;
    agents: string[];
    variants: string[];
    tasks: string[];
  };
};

type SaveResponse = {
  config_path: string;
  tasks_path: string;
  reloaded?: LoadedConfig;
};

type RunPlan = {
  case_count: number;
  cleanup_policy: string;
  jobs: number;
  trials: number;
  output_dir: string;
  agents: string[];
  tasks: string[];
  variants: string[];
  cases: {
    case_id: string;
    agent_name: string;
    agent_kind: string;
    task_id: string;
    variant: string;
    trial_index: number;
    repo_ref: string;
    command_preview: string;
    expected_outcome_summary?: string | null;
    hard_evaluation_enabled?: boolean;
    soft_evaluation_enabled?: boolean;
  }[];
};

type RunStatus = {
  app_run_id: string;
  status: string;
  run_dir: string | null;
  case_count: number;
  completed_cases: number;
  error?: string | null;
};

type ResultsPayload = {
  overview: {
    case_count: number;
    failed_count: number;
    timeout_count: number;
    low_confidence_count: number;
    telemetry_gap_count: number;
  };
  cases: {
    case_id: string;
    agent_name: string;
    task_id: string;
    variant: string;
    status: string;
    validation_status: string;
    confidence: string;
    changed_files?: number;
    hard_evaluation_status?: string;
    hard_evaluation_score?: number | null;
    hard_evaluation_max_score?: number | null;
    soft_evaluation_status?: string;
    soft_evaluation_payload_path?: string | null;
    patch_path?: string | null;
    stdout_path?: string | null;
    stderr_path?: string | null;
  }[];
};

type LogPayload = {
  console: string[];
  files: { path: string; tail: string }[];
};

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `请求失败: ${response.status}`);
  }
  return data as T;
}

function fallbackConfig(): LoadedConfig {
  const fallbackAgents: EditableAgent[] = localAppFixture.agents.map((agent) => ({
    name: agent.name,
    kind: agent.kind,
    command: agent.command,
    timeout_minutes: 60,
    network: 'disabled',
  }));
  const fallbackTasks: EditableTask[] = localAppFixture.tasks.map((task) => ({
    id: task,
    title: task,
    prompt: `Run ${task}.`,
    validation_commands: [],
    expected_outcome: {
      summary: '示例任务会生成本地补丁证据。',
      acceptance_points: ['本地结果可审查。'],
    },
    hard_evaluation: {
      enabled: true,
      require_validation_pass: false,
      required_paths: ['README.md'],
      forbidden_paths: [],
      expected_snippets: [],
      forbidden_snippets: [],
    },
    soft_evaluation: {
      enabled: true,
      mode: 'payload-only',
      max_score: 10,
      rubric: [{ name: 'quality', weight: 1, description: 'Patch is clear.' }],
    },
  }));
  const fallbackVariants: EditableVariant[] = localAppFixture.variants.map((variant) => ({
    name: variant,
    description: variant,
    overlays: [],
  }));
  const configYaml = [
    'repo:',
    '  path: ./fixture-repo',
    '  base_ref: main',
    'agents:',
    ...fallbackAgents.flatMap((agent) => [
      `  ${agent.name}:`,
      `    kind: ${agent.kind}`,
      `    command: ${JSON.stringify(agent.command)}`,
      '    timeout_minutes: 60',
      '    network: disabled',
    ]),
    'tasks: ./tasks.yaml',
    'output_dir: ./runs',
    'variants:',
    ...fallbackVariants.flatMap((variant) => [
      `  ${variant.name}:`,
      `    description: ${variant.description}`,
      '    overlays: []',
    ]),
    'evaluation:',
    '  commands: []',
    '',
  ].join('\n');
  const tasksYaml = [
    'tasks:',
    ...fallbackTasks.flatMap((task) => [
      `  - id: ${task.id}`,
      `    title: ${task.title}`,
      `    prompt: ${task.prompt}`,
      '    expected_outcome:',
      `      summary: ${task.expected_outcome?.summary}`,
      '    hard_evaluation:',
      '      enabled: true',
      '      required_paths: [README.md]',
      '    soft_evaluation:',
      '      enabled: true',
      '      mode: payload-only',
    ]),
    '',
  ].join('\n');
  return {
    config_path: 'context-eval.yaml',
    tasks_path: 'tasks.yaml',
    config_yaml: configYaml,
    tasks_yaml: tasksYaml,
    editable: {
      repo: { path: './fixture-repo', base_ref: 'main' },
      agent: fallbackAgents[0],
      agent_shape: 'agents',
      agents: fallbackAgents,
      tasks_path: './tasks.yaml',
      variants: fallbackVariants,
      tasks: fallbackTasks,
      evaluation_commands: [],
      output_dir: './runs',
    },
    resolved: {
      repo_path: './fixture-repo',
      output_dir: './runs',
      agents: fallbackAgents.map((agent) => agent.name),
      variants: fallbackVariants.map((variant) => variant.name),
      tasks: fallbackTasks.map((task) => task.id),
    },
  };
}

function splitLines(value: string) {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

const checkLabels: Record<string, string> = {
  schema: '配置结构',
  repo: '仓库路径',
  git_refs: 'Git 引用',
  overlay_paths: '上下文覆盖路径',
  task_ids: '任务 ID',
  prompt_templates: '提示模板',
  agent_command_variables: '本地代理命令变量',
  agent_executables: '本地代理可执行文件',
  agent_executables_skipped: '跳过可执行文件检查',
  output_dir_writable: '输出目录可写',
  side_effect_free: '无执行副作用',
};

const runStatusLabels: Record<string, string> = {
  queued: '排队中',
  running: '运行中',
  stop_requested: '正在停止',
  completed: '已完成',
  failed: '失败',
  internal_error: '内部错误',
};

const resultStatusLabels: Record<string, string> = {
  completed: '已完成',
  agent_failed: '本地代理失败',
  timeout: '超时',
  overlay_failed: '覆盖失败',
  workspace_failed: '工作区失败',
  validation_failed: '验证失败',
  internal_error: '内部错误',
};

const validationLabels: Record<string, string> = {
  passed: '通过',
  failed: '失败',
  skipped: '跳过',
};

function labelFor(labels: Record<string, string>, value: string | undefined | null) {
  if (!value) return '未知';
  return labels[value] ?? value;
}

function agentsFrom(loaded: LoadedConfig) {
  return loaded.editable.agent_shape === 'agents'
    ? loaded.editable.agents
    : [loaded.editable.agent];
}

function primaryTask(loaded: LoadedConfig) {
  return loaded.editable.tasks[0];
}

function primaryCocoAgent(loaded: LoadedConfig) {
  return agentsFrom(loaded).find((agent) => agent.kind === 'coco') || agentsFrom(loaded)[0];
}

function listText(values: string[] | undefined, fallback = '未配置') {
  return values && values.length > 0 ? values.join(', ') : fallback;
}

export function App() {
  const [serverMode, setServerMode] = useState<'checking' | 'connected' | 'fixture'>('checking');
  const [configPath, setConfigPath] = useState('context-eval.yaml');
  const [loaded, setLoaded] = useState<LoadedConfig>(() => fallbackConfig());
  const [configYaml, setConfigYaml] = useState(() => fallbackConfig().config_yaml);
  const [tasksYaml, setTasksYaml] = useState(() => fallbackConfig().tasks_yaml);
  const [saveStatus, setSaveStatus] = useState('尚未保存');
  const [preflightStatus, setPreflightStatus] = useState('等待预检');
  const [preflightChecks, setPreflightChecks] = useState<string[]>([]);
  const [plan, setPlan] = useState<RunPlan | null>(null);
  const [run, setRun] = useState<RunStatus | null>(null);
  const [logs, setLogs] = useState<LogPayload | null>(null);
  const [results, setResults] = useState<ResultsPayload | null>(null);
  const [exportOutput, setExportOutput] = useState('');
  const [error, setError] = useState('');
  const [cleanupPolicy, setCleanupPolicy] = useState('successful');

  const fixtureCaseCount = useMemo(() => plannedCaseCount(localAppFixture), []);
  const visibleCaseCount = plan?.case_count ?? fixtureCaseCount;
  const agents = agentsFrom(loaded);
  const cocoAgent = primaryCocoAgent(loaded);
  const task = primaryTask(loaded);

  function applyLoadedConfig(payload: LoadedConfig) {
    setLoaded(payload);
    setConfigPath(payload.config_path);
    setConfigYaml(payload.config_yaml);
    setTasksYaml(payload.tasks_yaml);
  }

  async function loadConfig(path = configPath) {
    setError('');
    if (serverMode === 'fixture') {
      applyLoadedConfig(fallbackConfig());
      setSaveStatus('示例配置已加载');
      return;
    }
    const payload = await apiRequest<LoadedConfig>('/api/config/load', {
      method: 'POST',
      body: JSON.stringify({ config_path: path }),
    });
    applyLoadedConfig(payload);
    setSaveStatus('已加载本地配置');
  }

  async function saveConfig() {
    setError('');
    const saved = await apiRequest<SaveResponse>('/api/config/save', {
      method: 'POST',
      body: JSON.stringify({
        config_path: loaded.config_path || configPath,
        tasks_path: loaded.tasks_path || 'tasks.yaml',
        config_yaml: configYaml,
        tasks_yaml: tasksYaml,
      }),
    });
    if (saved.reloaded) {
      applyLoadedConfig(saved.reloaded);
    } else {
      await loadConfig(saved.config_path);
    }
    setSaveStatus(`已保存并从磁盘重载: ${saved.config_path} / ${saved.tasks_path}`);
  }

  async function runPreflight() {
    setError('');
    const payload = await apiRequest<{ checks: string[] }>('/api/preflight', {
      method: 'POST',
      body: JSON.stringify({ config_path: loaded.config_path || configPath, check_agents: true }),
    });
    setPreflightChecks(payload.checks);
    setPreflightStatus('预检通过');
  }

  async function planRun() {
    setError('');
    const payload = await apiRequest<RunPlan>('/api/run-plan', {
      method: 'POST',
      body: JSON.stringify({
        config_path: loaded.config_path || configPath,
        cleanup_policy: cleanupPolicy,
      }),
    });
    setPlan(payload);
  }

  async function loadResultsForRun(status: RunStatus) {
    const logPayload = await apiRequest<LogPayload>(`/api/runs/${status.app_run_id}/logs`);
    setLogs(logPayload);
    if (status.run_dir && status.status === 'completed') {
      const resultPayload = await apiRequest<ResultsPayload>(
        `/api/results?run_dir=${encodeURIComponent(status.run_dir)}`,
      );
      setResults(resultPayload);
    }
  }

  async function refreshRunStatus(appRunId: string) {
    const status = await apiRequest<RunStatus>(`/api/runs/${appRunId}`);
    setRun(status);
    await loadResultsForRun(status);
    return status;
  }

  async function startRun() {
    setError('');
    const payload = await apiRequest<RunStatus>('/api/runs', {
      method: 'POST',
      body: JSON.stringify({
        config_path: loaded.config_path || configPath,
        cleanup_policy: cleanupPolicy,
        confirm: true,
      }),
    });
    setRun(payload);
    await loadResultsForRun(payload);
  }

  async function stopRun() {
    if (!run) return;
    const payload = await apiRequest<{ status: string }>(`/api/runs/${run.app_run_id}/stop`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
    setRun((current) => (current ? { ...current, status: payload.status } : current));
  }

  async function exportRun(format: string) {
    if (!run?.run_dir) return;
    const payload = await apiRequest<{ content: string }>(
      `/api/exports?run_dir=${encodeURIComponent(run.run_dir)}&format=${format}`,
    );
    setExportOutput(payload.content);
  }

  useEffect(() => {
    let cancelled = false;
    async function checkServer() {
      if (typeof fetch !== 'function') {
        setServerMode('fixture');
        return;
      }
      try {
        const health = await apiRequest<{ initial_config_path?: string | null }>('/api/health');
        if (cancelled) return;
        setServerMode('connected');
        if (health.initial_config_path) {
          setConfigPath(health.initial_config_path);
          await loadConfig(health.initial_config_path);
        }
      } catch {
        if (!cancelled) {
          setServerMode('fixture');
          applyLoadedConfig(fallbackConfig());
        }
      }
    }
    checkServer();
    return () => {
      cancelled = true;
    };
    // loadConfig intentionally reads serverMode; startup only needs the first health result.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!run || !['queued', 'running', 'stop_requested'].includes(run.status)) return;
    const timer = window.setInterval(() => {
      refreshRunStatus(run.app_run_id).catch((caught: Error) => setError(caught.message));
    }, 500);
    return () => window.clearInterval(timer);
  }, [run]);

  async function guarded(action: () => Promise<void>) {
    try {
      await action();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }

  const modeLabel = {
    checking: '检测中',
    connected: '本地回环服务',
    fixture: '示例模式',
  }[serverMode];
  const runLabel = run ? labelFor(runStatusLabels, run.status) : '待运行';

  return (
    <main className="app-shell" data-testid="local-app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">仅使用本地产物</p>
          <h1>context-eval 本地工作台</h1>
        </div>
        <div className="status-pill" aria-label="本地应用模式">
          {modeLabel}
        </div>
      </header>

      {error && <div className="notice error">错误: {error}</div>}

      <section className="workflow-band" aria-label="工作流状态">
        {[
          ['Project', loaded.resolved.repo_path],
          ['Coco Agent', cocoAgent?.name || '未配置'],
          ['Preflight', preflightStatus === '预检通过' ? '通过' : '等待'],
          ['Run', runLabel],
          ['Results', results ? '已加载' : '本地'],
        ].map(([label, state]) => (
          <div className="workflow-step" key={label}>
            <span>{label}</span>
            <strong>{state}</strong>
          </div>
        ))}
      </section>

      <section className="content-grid">
        <section className="panel project-panel">
          <div className="panel-heading">
            <h2>Project</h2>
            <span>{modeLabel}</span>
          </div>
          <div className="form-grid">
            <label htmlFor="config-path">
              配置路径
              <input
                id="config-path"
                value={configPath}
                onChange={(event) => setConfigPath(event.target.value)}
              />
            </label>
            <label htmlFor="repo-path">
              仓库路径
              <input id="repo-path" value={loaded.editable.repo.path} readOnly />
            </label>
            <label htmlFor="base-ref">
              base ref
              <input id="base-ref" value={loaded.editable.repo.base_ref} readOnly />
            </label>
            <label htmlFor="output-dir">
              输出目录
              <input id="output-dir" value={loaded.editable.output_dir || './runs'} readOnly />
            </label>
          </div>
          <div className="button-row">
            <button type="button" onClick={() => guarded(() => loadConfig())}>
              加载配置
            </button>
            <button type="button" onClick={() => guarded(saveConfig)} disabled={serverMode !== 'connected'}>
              保存并重载
            </button>
          </div>
          <p className="status-line" data-testid="save-status">
            {saveStatus}
          </p>
        </section>

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
              <dd>{loaded.editable.tasks.length}</dd>
            </div>
            <div>
              <dt>variants</dt>
              <dd>{loaded.editable.variants.length}</dd>
            </div>
            <div>
              <dt>trials</dt>
              <dd>{plan?.trials ?? localAppFixture.trials}</dd>
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
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Coco Agent</h2>
            <span>{cocoAgent?.kind || 'unknown'}</span>
          </div>
          <ul className="profile-list">
            {agents.map((profile) => (
              <li key={profile.name}>
                <div>
                  <strong>{profile.name}</strong>
                  <span>{profile.kind}</span>
                </div>
                <code>{profile.command}</code>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Context Variants</h2>
          </div>
          <ul className="two-column-list single-list">
            {loaded.editable.variants.map((variant) => (
              <li key={variant.name}>
                <strong>{variant.name}</strong>
                <span>{variant.description || '未描述'}</span>
                <small>{variant.overlays.length} overlay(s)</small>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Tasks</h2>
            <span>{loaded.editable.tasks.length}</span>
          </div>
          <ul className="two-column-list single-list">
            {loaded.editable.tasks.map((item) => (
              <li key={item.id}>
                <strong>{item.id}</strong>
                <span>{item.title || item.prompt}</span>
                <small>{[item.category, item.difficulty].filter(Boolean).join(' / ')}</small>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Expected Outcome</h2>
          </div>
          <p className="status-line">{task?.expected_outcome?.summary || '未配置 summary'}</p>
          <ul className="check-list">
            {(task?.expected_outcome?.acceptance_points || []).map((point) => (
              <li key={point}>{point}</li>
            ))}
            {task?.expected_outcome?.files?.map((file) => (
              <li key={file.path}>
                <strong>{file.path}</strong>
                <span>{file.must_change ? 'must_change' : file.change_type || 'expected'}</span>
              </li>
            ))}
            {(!task?.expected_outcome?.acceptance_points?.length
              && !task?.expected_outcome?.files?.length) && <li>未配置 acceptance_points 或 files</li>}
          </ul>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Hard Evaluation</h2>
            <span>{task?.hard_evaluation?.enabled ? 'enabled' : 'disabled'}</span>
          </div>
          <dl className="compact-list">
            <div>
              <dt>require_validation_pass</dt>
              <dd>{String(Boolean(task?.hard_evaluation?.require_validation_pass))}</dd>
            </div>
            <div>
              <dt>required_paths</dt>
              <dd>{listText(task?.hard_evaluation?.required_paths)}</dd>
            </div>
            <div>
              <dt>forbidden_paths</dt>
              <dd>{listText(task?.hard_evaluation?.forbidden_paths)}</dd>
            </div>
          </dl>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Soft Evaluation</h2>
            <span>{task?.soft_evaluation?.mode || 'not_configured'}</span>
          </div>
          <ul className="check-list">
            {(task?.soft_evaluation?.rubric || []).map((rubric) => (
              <li key={rubric.name}>
                <strong>{rubric.name}</strong>
                <span>{rubric.description}</span>
                <small>weight={rubric.weight}</small>
              </li>
            ))}
            {!task?.soft_evaluation?.rubric?.length && <li>未配置 rubric</li>}
          </ul>
        </section>

        <section className="panel yaml-panel">
          <div className="panel-heading">
            <h2>配置文件</h2>
          </div>
          <label htmlFor="config-yaml">
            context-eval.yaml
            <textarea
              id="config-yaml"
              value={configYaml}
              onChange={(event) => setConfigYaml(event.target.value)}
              spellCheck={false}
            />
          </label>
          <label htmlFor="tasks-yaml">
            tasks.yaml
            <textarea
              id="tasks-yaml"
              value={tasksYaml}
              onChange={(event) => setTasksYaml(event.target.value)}
              spellCheck={false}
            />
          </label>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Run Execution</h2>
          </div>
          <label htmlFor="cleanup-policy">
            清理策略
            <select
              id="cleanup-policy"
              value={cleanupPolicy}
              onChange={(event) => setCleanupPolicy(event.target.value)}
            >
              <option value="never">保留所有工作区</option>
              <option value="always">总是清理</option>
              <option value="successful">成功后清理</option>
              <option value="failed">失败后清理</option>
            </select>
          </label>
          <div className="button-row">
            <button type="button" onClick={() => guarded(runPreflight)} disabled={serverMode !== 'connected'}>
              运行预检
            </button>
            <button type="button" onClick={() => guarded(planRun)} disabled={serverMode !== 'connected'}>
              生成计划
            </button>
            <button type="button" onClick={() => guarded(startRun)} disabled={serverMode !== 'connected'}>
              开始运行
            </button>
            <button type="button" className="secondary" onClick={() => guarded(stopRun)} disabled={!run}>
              停止
            </button>
          </div>
          <p className="status-line" data-testid="preflight-status">
            {preflightStatus}
          </p>
          <p className="status-line">
            计划用例: <strong data-testid="planned-case-count">{plan?.case_count ?? 0}</strong>
          </p>
          <ul className="check-list">
            {preflightChecks.map((check) => (
              <li key={check}>{labelFor(checkLabels, check)}</li>
            ))}
          </ul>
        </section>

        <section className="panel run-panel">
          <div className="panel-heading">
            <h2>运行进度</h2>
          </div>
          <p className="run-status" data-testid="run-status">
            {run ? `${labelFor(runStatusLabels, run.status)} ${run.completed_cases}/${run.case_count}` : '待运行'}
          </p>
          <div className="log-box" aria-live="polite">
            {(logs?.console || []).map((line) => (
              <code key={line}>{line}</code>
            ))}
            {(!logs || logs.console.length === 0) && <span>暂无日志</span>}
          </div>
          <div className="log-files">
            {(logs?.files || []).slice(0, 4).map((file) => (
              <details key={file.path}>
                <summary>{file.path}</summary>
                <pre>{file.tail}</pre>
              </details>
            ))}
          </div>
        </section>

        <section className="panel results-panel">
          <div className="panel-heading">
            <h2>Results</h2>
            <span>{results?.overview.case_count ?? 0}</span>
          </div>
          {results ? (
            <>
              <dl className="metric-grid">
                <div>
                  <dt>failed</dt>
                  <dd>{results.overview.failed_count}</dd>
                </div>
                <div>
                  <dt>timeouts</dt>
                  <dd>{results.overview.timeout_count}</dd>
                </div>
                <div>
                  <dt>low confidence</dt>
                  <dd>{results.overview.low_confidence_count}</dd>
                </div>
                <div>
                  <dt>telemetry gaps</dt>
                  <dd>{results.overview.telemetry_gap_count}</dd>
                </div>
              </dl>
              <table>
                <thead>
                  <tr>
                    <th>case</th>
                    <th>agent</th>
                    <th>status</th>
                    <th>validation</th>
                    <th>hard</th>
                    <th>soft</th>
                  </tr>
                </thead>
                <tbody>
                  {results.cases.map((result) => (
                    <tr key={result.case_id}>
                      <td>{result.task_id}</td>
                      <td>{result.agent_name}</td>
                      <td>{labelFor(resultStatusLabels, result.status)}</td>
                      <td>{labelFor(validationLabels, result.validation_status)}</td>
                      <td>
                        hard {result.hard_evaluation_status || 'not_configured'}{' '}
                        {result.hard_evaluation_score ?? '-'}
                        /
                        {result.hard_evaluation_max_score ?? '-'}
                      </td>
                      <td>soft {result.soft_evaluation_status || 'not_configured'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : (
            <p className="status-line">运行完成后显示本地结果。</p>
          )}
          <div className="button-row">
            <button type="button" onClick={() => guarded(() => exportRun('json'))} disabled={!run?.run_dir}>
              导出 JSON
            </button>
            <button type="button" onClick={() => guarded(() => exportRun('csv'))} disabled={!run?.run_dir}>
              导出 CSV
            </button>
            <button type="button" onClick={() => guarded(() => exportRun('markdown'))} disabled={!run?.run_dir}>
              导出 Markdown
            </button>
            <button type="button" onClick={() => guarded(() => exportRun('html'))} disabled={!run?.run_dir}>
              导出 HTML
            </button>
          </div>
          <pre className="export-output" data-testid="export-output">
            {exportOutput}
          </pre>
        </section>
      </section>
    </main>
  );
}
