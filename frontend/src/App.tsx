import { useEffect, useMemo, useRef, useState } from 'react';
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

type WorkspaceState = {
  state: 'empty' | 'configured';
  has_config: boolean;
  default_config_path: string;
  config_path?: string | null;
  workspace_root?: string;
};

type BootstrapResponse = WorkspaceState & {
  loaded?: LoadedConfig;
  config_path?: string | null;
  tasks_path?: string | null;
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

type ManualReview = {
  case_id: string;
  decision: string;
  confidence: string;
  reviewer: string;
  notes: string;
  updated_at?: string | null;
};

type ResultCase = {
  case_id: string;
  agent_name: string;
  task_id: string;
  variant: string;
  status: string;
  validation_status: string;
  confidence: string;
  telemetry_status?: string;
  agent_duration_seconds?: number | null;
  total_tokens?: number | null;
  reasoning_tokens?: number | null;
  reasoning_step_count?: number | null;
  tool_call_count?: number | null;
  changed_files?: number;
  hard_evaluation_status?: string;
  hard_evaluation_score?: number | null;
  hard_evaluation_max_score?: number | null;
  soft_evaluation_status?: string;
  soft_evaluation_payload_path?: string | null;
  patch_path?: string | null;
  stdout_path?: string | null;
  stderr_path?: string | null;
  manual_review?: ManualReview;
};

type ResultsPayload = {
  overview: {
    case_count: number;
    failed_count: number;
    timeout_count: number;
    low_confidence_count: number;
    telemetry_gap_count: number;
  };
  compare_groups?: {
    group_id: string;
    task_id: string;
    agent_name: string;
    trial_index: number;
    baseline_variant: string;
    experiment_variant: string;
    baseline_case_id: string;
    experiment_case_id: string;
    verdict: string;
    hard_delta: number;
    validation_delta: number;
    total_tokens_delta?: number | null;
    summary: string;
  }[];
  cases: ResultCase[];
};

type ArtifactContent = {
  path: string;
  content: string;
  exists: boolean;
  error?: string;
};

type CaseDetailPayload = {
  case: ResultCase;
  patch?: ArtifactContent | null;
  prompt?: ArtifactContent | null;
  logs: (ArtifactContent & { kind: string })[];
  hard_evaluation?: unknown;
  soft_evaluation?: unknown;
  manual_review: ManualReview;
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

function emptyConfig(): LoadedConfig {
  return {
    config_path: 'context-eval.yaml',
    tasks_path: 'tasks.yaml',
    config_yaml: '',
    tasks_yaml: '',
    editable: {
      repo: { path: '', base_ref: 'main' },
      agent: {
        name: '',
        kind: 'custom',
        command: '',
        timeout_minutes: 60,
        network: 'disabled',
      },
      agent_shape: 'agent',
      agents: [],
      tasks_path: './tasks.yaml',
      variants: [],
      tasks: [],
      evaluation_commands: [],
      output_dir: './runs',
    },
    resolved: {
      repo_path: '',
      output_dir: './runs',
      agents: [],
      variants: [],
      tasks: [],
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

function primaryAgent(loaded: LoadedConfig) {
  return agentsFrom(loaded).find((agent) => agent.kind === 'coco') || agentsFrom(loaded)[0];
}

function listText(values: string[] | undefined, fallback = '未配置') {
  return values && values.length > 0 ? values.join(', ') : fallback;
}

export function App() {
  const resultsPanelRef = useRef<HTMLElement | null>(null);
  const shouldRevealResultsRef = useRef(false);
  const [serverMode, setServerMode] = useState<'checking' | 'connected' | 'fixture'>('checking');
  const [configPath, setConfigPath] = useState('context-eval.yaml');
  const [loaded, setLoaded] = useState<LoadedConfig>(() => emptyConfig());
  const [configYaml, setConfigYaml] = useState('');
  const [tasksYaml, setTasksYaml] = useState('');
  const [saveStatus, setSaveStatus] = useState('尚未保存');
  const [preflightStatus, setPreflightStatus] = useState('待检查');
  const [preflightChecks, setPreflightChecks] = useState<string[]>([]);
  const [plan, setPlan] = useState<RunPlan | null>(null);
  const [run, setRun] = useState<RunStatus | null>(null);
  const [logs, setLogs] = useState<LogPayload | null>(null);
  const [results, setResults] = useState<ResultsPayload | null>(null);
  const [selectedCaseId, setSelectedCaseId] = useState('');
  const [caseDetail, setCaseDetail] = useState<CaseDetailPayload | null>(null);
  const [reviewDraft, setReviewDraft] = useState<ManualReview>({
    case_id: '',
    decision: 'not_reviewed',
    confidence: 'unknown',
    reviewer: '',
    notes: '',
    updated_at: null,
  });
  const [reviewStatus, setReviewStatus] = useState('');
  const [exportOutput, setExportOutput] = useState('');
  const [error, setError] = useState('');
  const [cleanupPolicy, setCleanupPolicy] = useState('successful');
  const [workspaceState, setWorkspaceState] = useState<WorkspaceState | null>(null);
  const [projectRepoPath, setProjectRepoPath] = useState('');
  const [configLoaded, setConfigLoaded] = useState(false);

  const fixtureCaseCount = useMemo(() => plannedCaseCount(localAppFixture), []);
  const agents = agentsFrom(loaded);
  const cocoAgent = primaryAgent(loaded);
  const task = primaryTask(loaded);
  const estimatedCaseCount =
    agents.length * loaded.editable.tasks.length * loaded.editable.variants.length;
  const visibleCaseCount = plan?.case_count ?? (serverMode === 'fixture' ? fixtureCaseCount : estimatedCaseCount);

  function applyLoadedConfig(payload: LoadedConfig) {
    setLoaded(payload);
    setConfigPath(payload.config_path);
    setConfigYaml(payload.config_yaml);
    setTasksYaml(payload.tasks_yaml);
    setConfigLoaded(true);
    setWorkspaceState((current) => ({
      state: 'configured',
      has_config: true,
      default_config_path: current?.default_config_path || payload.config_path,
      config_path: payload.config_path,
      workspace_root: current?.workspace_root,
    }));
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

  async function bootstrapDemo() {
    setError('');
    const payload = await apiRequest<BootstrapResponse>('/api/demo/bootstrap', {
      method: 'POST',
      body: JSON.stringify({ overwrite: false }),
    });
    setWorkspaceState(payload);
    if (payload.loaded) {
      applyLoadedConfig(payload.loaded);
    } else {
      await loadConfig(payload.config_path || 'context-eval.yaml');
    }
    setSaveStatus('demo 工作区已创建');
  }

  async function initializeProject() {
    setError('');
    const payload = await apiRequest<BootstrapResponse>('/api/workspace/project', {
      method: 'POST',
      body: JSON.stringify({ repo_path: projectRepoPath, overwrite: false }),
    });
    setWorkspaceState(payload);
    if (payload.loaded) {
      applyLoadedConfig(payload.loaded);
    } else {
      await loadConfig(payload.config_path || 'context-eval.yaml');
    }
    setSaveStatus('真实项目配置已创建，请检查 agent 命令和任务');
  }

  async function runPreflight() {
    setPreflightStatus('正在检查配置和本地执行条件');
    const payload = await apiRequest<{ checks: string[] }>('/api/preflight', {
      method: 'POST',
      body: JSON.stringify({ config_path: loaded.config_path || configPath, check_agents: true }),
    });
    setPreflightChecks(payload.checks);
    setPreflightStatus('运行前检查通过');
    return payload.checks;
  }

  async function planRun() {
    const payload = await apiRequest<RunPlan>('/api/run-plan', {
      method: 'POST',
      body: JSON.stringify({
        config_path: loaded.config_path || configPath,
        cleanup_policy: cleanupPolicy,
      }),
    });
    setPlan(payload);
    return payload;
  }

  async function loadResultsForRun(status: RunStatus) {
    const logPayload = await apiRequest<LogPayload>(`/api/runs/${status.app_run_id}/logs`);
    setLogs(logPayload);
    if (status.run_dir && status.status === 'completed') {
      await loadResults(status.run_dir);
    }
  }

  async function loadResults(runDir: string) {
    const resultPayload = await apiRequest<ResultsPayload>(
      `/api/results?run_dir=${encodeURIComponent(runDir)}`,
    );
    setResults(resultPayload);
    if (selectedCaseId && !resultPayload.cases.some((item) => item.case_id === selectedCaseId)) {
      setSelectedCaseId('');
      setCaseDetail(null);
    }
  }

  async function loadCaseDetail(caseId: string) {
    if (!run?.run_dir) return;
    const detail = await apiRequest<CaseDetailPayload>(
      `/api/case-detail?run_dir=${encodeURIComponent(run.run_dir)}&case_id=${encodeURIComponent(caseId)}`,
    );
    setSelectedCaseId(caseId);
    setCaseDetail(detail);
    setReviewDraft(detail.manual_review);
  }

  async function saveManualReview() {
    if (!run?.run_dir || !selectedCaseId) return;
    const payload = await apiRequest<{ review: ManualReview }>('/api/manual-review', {
      method: 'POST',
      body: JSON.stringify({
        run_dir: run.run_dir,
        case_id: selectedCaseId,
        review: {
          decision: reviewDraft.decision,
          confidence: reviewDraft.confidence,
          reviewer: reviewDraft.reviewer,
          notes: reviewDraft.notes,
        },
      }),
    });
    setReviewDraft(payload.review);
    await loadResults(run.run_dir);
    await loadCaseDetail(selectedCaseId);
    setReviewStatus('Review 已保存');
  }

  async function refreshRunStatus(appRunId: string) {
    const status = await apiRequest<RunStatus>(`/api/runs/${appRunId}`);
    setRun(status);
    await loadResultsForRun(status);
    return status;
  }

  async function startRun() {
    setError('');
    setResults(null);
    setSelectedCaseId('');
    setCaseDetail(null);
    setReviewStatus('');
    setExportOutput('');
    setLogs(null);
    setPlan(null);
    shouldRevealResultsRef.current = true;
    try {
      await runPreflight();
      await planRun();
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
    } catch (caught) {
      setPreflightStatus('运行前准备失败');
      throw caught;
    }
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
        const health = await apiRequest<{
          initial_config_path?: string | null;
          workspace?: WorkspaceState;
        }>('/api/health');
        if (cancelled) return;
        setServerMode('connected');
        if (health.workspace) {
          setWorkspaceState(health.workspace);
        }
        if (health.initial_config_path) {
          setConfigPath(health.initial_config_path);
          await loadConfig(health.initial_config_path);
        } else if (health.workspace?.has_config) {
          await loadConfig(health.workspace.config_path || 'context-eval.yaml');
        } else {
          setConfigLoaded(false);
          setLoaded(emptyConfig());
          setConfigYaml('');
          setTasksYaml('');
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

  useEffect(() => {
    if (!results || !shouldRevealResultsRef.current) return;
    shouldRevealResultsRef.current = false;
    const reveal = () => {
      resultsPanelRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
    };
    if (typeof window.requestAnimationFrame === 'function') {
      window.requestAnimationFrame(reveal);
    } else {
      reveal();
    }
  }, [results]);

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
  const isRunActive = Boolean(run && ['queued', 'running', 'stop_requested'].includes(run.status));
  const resultSummary = results
    ? {
        validationFailed: results.cases.filter((result) => result.validation_status === 'failed').length,
        hardFailed: results.cases.filter((result) => result.hard_evaluation_status === 'failed').length,
      }
    : null;
  const preflightStepLabel =
    preflightStatus === '运行前检查通过'
      ? '通过'
      : preflightStatus === '待检查'
        ? '自动'
        : preflightStatus;
  const taskTitle = task?.title || task?.id || '未配置任务';
  const variantSummary = loaded.editable.variants.map((variant) => variant.name).join(' vs ') || '未配置 context';
  const runBrief = configLoaded
    ? `用 ${cocoAgent?.name || '未配置 agent'} 在 ${variantSummary} 上执行 ${loaded.editable.tasks.length} 个任务，共 ${visibleCaseCount} 个 case。`
    : '先试用 demo 或打开一个本地 Git 项目。';

  const isFirstRun = serverMode === 'connected' && workspaceState?.state === 'empty' && !configLoaded;

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
          ['Agent', cocoAgent?.name || '未配置'],
          ['Preflight', preflightStepLabel],
          ['Run', runLabel],
          ['Results', results ? '已加载' : '本地'],
        ].map(([label, state]) => (
          <div className="workflow-step" key={label}>
            <span>{label}</span>
            <strong>{state}</strong>
          </div>
        ))}
      </section>

      {isFirstRun && (
        <section className="first-run-panel" aria-label="首次设置">
          <div className="panel-heading">
            <h2>开始使用</h2>
            <span>空工作区</span>
          </div>
          <div className="first-run-grid">
            <article className="setup-option">
              <div>
                <strong>试用 demo</strong>
                <p>创建一个本地 demo repo、两组 context variants、一个 fake agent 和可对比的硬检查结果。</p>
              </div>
              <button type="button" onClick={() => guarded(bootstrapDemo)}>
                试用 demo
              </button>
            </article>
            <article className="setup-option">
              <div>
                <strong>打开真实项目</strong>
                <p>从已有 Git 仓库生成评测工作区，然后继续配置 agent、context 和任务。</p>
              </div>
              <label htmlFor="project-repo-path">
                项目路径
                <input
                  id="project-repo-path"
                  value={projectRepoPath}
                  onChange={(event) => setProjectRepoPath(event.target.value)}
                  placeholder="D:\\path\\to\\repo"
                />
              </label>
              <button
                type="button"
                onClick={() => guarded(initializeProject)}
                disabled={!projectRepoPath.trim()}
              >
                创建工作区
              </button>
            </article>
          </div>
        </section>
      )}

      {!isFirstRun && (
      <section className="content-grid">
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
          {!plan && (
            <p className="panel-note">点击“开始运行”后会自动展开具体 case，并在失败时把配置或执行错误显示出来。</p>
          )}
        </section>
        <details className="advanced-workbench">
          <summary>
            <span>配置与任务细节</span>
            <small>Agent、Context、验收标准和 YAML</small>
          </summary>
          <div className="advanced-grid">
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

        <section className="panel">
          <div className="panel-heading">
            <h2>Agent</h2>
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
          </div>
        </details>

        <section className="panel run-brief-panel">
          <div className="panel-heading">
            <h2>本次评测</h2>
            <span>{results ? '已出结果' : isRunActive ? '运行中' : '待运行'}</span>
          </div>
          <div className="brief-layout">
            <div className="brief-copy">
              <strong>{taskTitle}</strong>
              <span>{task?.expected_outcome?.summary || '未配置 expected_outcome summary'}</span>
              <p>{runBrief}</p>
            </div>
            <div className="brief-actions">
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
                <button type="button" onClick={() => guarded(startRun)} disabled={serverMode !== 'connected' || isRunActive}>
                  {isRunActive ? '运行中' : '开始运行'}
                </button>
                <button type="button" className="secondary" onClick={() => guarded(stopRun)} disabled={!isRunActive}>
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
              <dt>待执行 case</dt>
              <dd>
                <strong data-testid="planned-case-count">{plan?.case_count ?? visibleCaseCount}</strong>
                {!plan && visibleCaseCount > 0 && <small>预计</small>}
              </dd>
            </div>
          </dl>
          {preflightChecks.length > 0 && (
            <details className="prep-details">
              <summary>已通过 {preflightChecks.length} 项运行前检查</summary>
              <ul className="inline-check-list">
                {preflightChecks.map((check) => (
                  <li key={check}>{labelFor(checkLabels, check)}</li>
                ))}
              </ul>
            </details>
          )}
          {results && (
            <div className="result-callout" role="status">
              <div>
                <strong>结果已生成</strong>
                <span>
                  {results.overview.case_count} 个 case，validation failed {resultSummary?.validationFailed ?? 0}，
                  hard failed {resultSummary?.hardFailed ?? 0}，telemetry gaps {results.overview.telemetry_gap_count}
                </span>
              </div>
              <button
                type="button"
                className="secondary"
                onClick={() => resultsPanelRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })}
              >
                查看 Results
              </button>
            </div>
          )}
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

        <section className="panel results-panel" ref={resultsPanelRef}>
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
              {(results.compare_groups || []).length > 0 && (
                <section className="compare-summary" aria-label="baseline experiment compare">
                  <div className="panel-heading compact-heading">
                    <h3>Compare Summary</h3>
                    <span>{results.compare_groups?.length ?? 0}</span>
                  </div>
                  <div className="compare-grid">
                    {(results.compare_groups || []).map((group) => (
                      <article className="compare-card" key={group.group_id}>
                        <div>
                          <strong>{group.verdict}</strong>
                          <span>{group.summary}</span>
                        </div>
                        <dl>
                          <div>
                            <dt>task</dt>
                            <dd>{group.task_id}</dd>
                          </div>
                          <div>
                            <dt>hard delta</dt>
                            <dd>{group.hard_delta > 0 ? `+${group.hard_delta}` : group.hard_delta}</dd>
                          </div>
                          <div>
                            <dt>validation delta</dt>
                            <dd>
                              {group.validation_delta > 0 ? `+${group.validation_delta}` : group.validation_delta}
                            </dd>
                          </div>
                          <div>
                            <dt>tokens delta</dt>
                            <dd>{group.total_tokens_delta ?? '-'}</dd>
                          </div>
                        </dl>
                      </article>
                    ))}
                  </div>
                </section>
              )}
              <table>
                <thead>
                  <tr>
                    <th>case</th>
                    <th>agent</th>
                    <th>status</th>
                    <th>validation</th>
                    <th>telemetry</th>
                    <th>tokens</th>
                    <th>tools</th>
                    <th>hard</th>
                    <th>soft</th>
                    <th>review</th>
                    <th>detail</th>
                  </tr>
                </thead>
                <tbody>
                  {results.cases.map((result) => (
                    <tr key={result.case_id} className={selectedCaseId === result.case_id ? 'selected-row' : ''}>
                      <td data-label="case">
                        {result.task_id}
                        <small>{result.variant}</small>
                      </td>
                      <td data-label="agent">{result.agent_name}</td>
                      <td data-label="status">{labelFor(resultStatusLabels, result.status)}</td>
                      <td data-label="validation">{labelFor(validationLabels, result.validation_status)}</td>
                      <td data-label="telemetry">
                        {result.telemetry_status || 'unavailable'}
                        {result.agent_duration_seconds != null && (
                          <small>{result.agent_duration_seconds.toFixed(1)}s</small>
                        )}
                      </td>
                      <td data-label="tokens">
                        {result.total_tokens ?? '-'}
                        {result.reasoning_tokens != null && <small>reasoning {result.reasoning_tokens}</small>}
                      </td>
                      <td data-label="tools">
                        {result.tool_call_count ?? '-'}
                        {result.reasoning_step_count != null && <small>rounds {result.reasoning_step_count}</small>}
                      </td>
                      <td data-label="hard">
                        hard {result.hard_evaluation_status || 'not_configured'}{' '}
                        {result.hard_evaluation_score ?? '-'}
                        /
                        {result.hard_evaluation_max_score ?? '-'}
                      </td>
                      <td data-label="soft">soft {result.soft_evaluation_status || 'not_configured'}</td>
                      <td data-label="review">
                        {result.manual_review?.decision || 'not_reviewed'}
                        {result.manual_review?.confidence && <small>{result.manual_review.confidence}</small>}
                      </td>
                      <td data-label="detail">
                        <button
                          type="button"
                          className="secondary compact-button"
                          onClick={() => guarded(() => loadCaseDetail(result.case_id))}
                        >
                          查看详情
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {caseDetail && (
                <section className="case-detail-panel">
                  <div className="panel-heading compact-heading">
                    <h3>Case Detail</h3>
                    <span>{caseDetail.case.variant}</span>
                  </div>
                  <div className="detail-grid">
                    <dl className="compact-list">
                      <div>
                        <dt>case_id</dt>
                        <dd>{caseDetail.case.case_id}</dd>
                      </div>
                      <div>
                        <dt>status</dt>
                        <dd>{caseDetail.case.status}</dd>
                      </div>
                      <div>
                        <dt>validation</dt>
                        <dd>{caseDetail.case.validation_status}</dd>
                      </div>
                      <div>
                        <dt>hard</dt>
                        <dd>
                          {caseDetail.case.hard_evaluation_status}{' '}
                          {caseDetail.case.hard_evaluation_score ?? '-'}/
                          {caseDetail.case.hard_evaluation_max_score ?? '-'}
                        </dd>
                      </div>
                    </dl>
                    <form
                      className="review-form"
                      onSubmit={(event) => {
                        event.preventDefault();
                        guarded(saveManualReview);
                      }}
                    >
                      <label htmlFor="review-decision">
                        decision
                        <select
                          id="review-decision"
                          aria-label="review decision"
                          value={reviewDraft.decision}
                          onChange={(event) =>
                            setReviewDraft((current) => ({ ...current, decision: event.target.value }))
                          }
                        >
                          <option value="not_reviewed">not_reviewed</option>
                          <option value="pass">pass</option>
                          <option value="fail">fail</option>
                          <option value="needs_review">needs_review</option>
                        </select>
                      </label>
                      <label htmlFor="review-confidence">
                        confidence
                        <select
                          id="review-confidence"
                          aria-label="review confidence"
                          value={reviewDraft.confidence}
                          onChange={(event) =>
                            setReviewDraft((current) => ({ ...current, confidence: event.target.value }))
                          }
                        >
                          <option value="unknown">unknown</option>
                          <option value="low">low</option>
                          <option value="medium">medium</option>
                          <option value="high">high</option>
                        </select>
                      </label>
                      <label htmlFor="reviewer">
                        reviewer
                        <input
                          id="reviewer"
                          aria-label="reviewer"
                          value={reviewDraft.reviewer}
                          onChange={(event) =>
                            setReviewDraft((current) => ({ ...current, reviewer: event.target.value }))
                          }
                        />
                      </label>
                      <label htmlFor="review-notes">
                        notes
                        <textarea
                          id="review-notes"
                          aria-label="review notes"
                          value={reviewDraft.notes}
                          onChange={(event) =>
                            setReviewDraft((current) => ({ ...current, notes: event.target.value }))
                          }
                        />
                      </label>
                      <div className="button-row">
                        <button type="submit">保存 Review</button>
                        {reviewStatus && <span className="status-line">{reviewStatus}</span>}
                      </div>
                    </form>
                  </div>
                  <div className="artifact-grid">
                    {caseDetail.patch && (
                      <article className="artifact-pane">
                        <strong>{caseDetail.patch.path}</strong>
                        <pre>{caseDetail.patch.content || caseDetail.patch.error || 'empty patch'}</pre>
                      </article>
                    )}
                    {caseDetail.logs.slice(0, 4).map((log) => (
                      <article className="artifact-pane" key={`${log.kind}:${log.path}`}>
                        <strong>
                          {log.kind}: {log.path}
                        </strong>
                        <pre>{log.content || log.error || 'empty log'}</pre>
                      </article>
                    ))}
                  </div>
                </section>
              )}
            </>
          ) : (
            <p className="status-line">运行完成后显示本地结果。</p>
          )}
          {run?.run_dir && (
            <div className="button-row export-actions">
              <button type="button" onClick={() => guarded(() => exportRun('json'))}>
                导出 JSON
              </button>
              <button type="button" onClick={() => guarded(() => exportRun('csv'))}>
                导出 CSV
              </button>
              <button type="button" onClick={() => guarded(() => exportRun('markdown'))}>
                导出 Markdown
              </button>
              <button type="button" onClick={() => guarded(() => exportRun('html'))}>
                导出 HTML
              </button>
            </div>
          )}
          {exportOutput && (
            <pre className="export-output" data-testid="export-output">
              {exportOutput}
            </pre>
          )}
        </section>
      </section>
      )}
    </main>
  );
}
