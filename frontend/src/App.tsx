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

type EditableTask = {
  id: string;
  title?: string | null;
  prompt: string;
  category?: string | null;
  difficulty?: string | null;
  validation_commands: string[];
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
    throw new Error(data.error || `Request failed: ${response.status}`);
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
    prompt: task,
    validation_commands: [],
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

export function App() {
  const [serverMode, setServerMode] = useState<'checking' | 'connected' | 'fixture'>('checking');
  const [configPath, setConfigPath] = useState('context-eval.yaml');
  const [loaded, setLoaded] = useState<LoadedConfig>(() => fallbackConfig());
  const [configYaml, setConfigYaml] = useState(() => fallbackConfig().config_yaml);
  const [tasksYaml, setTasksYaml] = useState(() => fallbackConfig().tasks_yaml);
  const [saveStatus, setSaveStatus] = useState('No save yet');
  const [preflightStatus, setPreflightStatus] = useState('Preflight pending');
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
  const agents = loaded.editable.agent_shape === 'agents'
    ? loaded.editable.agents
    : [loaded.editable.agent];

  async function loadConfig(path = configPath) {
    setError('');
    if (serverMode === 'fixture') {
      const fallback = fallbackConfig();
      setLoaded(fallback);
      setConfigYaml(fallback.config_yaml);
      setTasksYaml(fallback.tasks_yaml);
      return;
    }
    const payload = await apiRequest<LoadedConfig>('/api/config/load', {
      method: 'POST',
      body: JSON.stringify({ config_path: path }),
    });
    setLoaded(payload);
    setConfigPath(payload.config_path);
    setConfigYaml(payload.config_yaml);
    setTasksYaml(payload.tasks_yaml);
    setSaveStatus('Loaded local config');
  }

  async function saveConfig() {
    setError('');
    const saved = await apiRequest<{ config_path: string; tasks_path: string }>('/api/config/save', {
      method: 'POST',
      body: JSON.stringify({
        config_path: loaded.config_path || configPath,
        tasks_path: loaded.tasks_path || 'tasks.yaml',
        config_yaml: configYaml,
        tasks_yaml: tasksYaml,
      }),
    });
    setSaveStatus(`Saved ${saved.config_path} and ${saved.tasks_path}`);
  }

  async function runPreflight() {
    setError('');
    const payload = await apiRequest<{ checks: string[] }>('/api/preflight', {
      method: 'POST',
      body: JSON.stringify({ config_path: loaded.config_path || configPath, check_agents: true }),
    });
    setPreflightChecks(payload.checks);
    setPreflightStatus('Preflight passed');
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

  async function refreshRunStatus(appRunId: string) {
    const status = await apiRequest<RunStatus>(`/api/runs/${appRunId}`);
    setRun(status);
    const logPayload = await apiRequest<LogPayload>(`/api/runs/${appRunId}/logs`);
    setLogs(logPayload);
    if (status.run_dir && status.status === 'completed') {
      const resultPayload = await apiRequest<ResultsPayload>(
        `/api/results?run_dir=${encodeURIComponent(status.run_dir)}`,
      );
      setResults(resultPayload);
    }
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
          setLoaded(fallbackConfig());
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

  return (
    <main className="app-shell" data-testid="local-app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Local artifacts only</p>
          <h1>Context Eval Local App</h1>
        </div>
        <div className="status-pill" aria-label="Local app mode">
          {serverMode === 'connected' ? 'Loopback server' : 'Validation shell'}
        </div>
      </header>

      {error && <div className="notice error">{error}</div>}

      <section className="workflow-band" aria-label="Workflow state">
        {[
          ['Project', loaded.resolved.repo_path],
          ['Profiles', String(agents.length)],
          ['Preflight', preflightStatus.includes('passed') ? 'Passed' : 'Pending'],
          ['Run', run?.status ?? 'Idle'],
          ['Results', results ? 'Loaded' : 'Local'],
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
            <h2>Project Setup</h2>
            <span>{serverMode}</span>
          </div>
          <div className="form-grid">
            <label htmlFor="config-path">
              Config path
              <input
                id="config-path"
                value={configPath}
                onChange={(event) => setConfigPath(event.target.value)}
              />
            </label>
            <label htmlFor="repo-path">
              Repo path
              <input id="repo-path" value={loaded.editable.repo.path} readOnly />
            </label>
            <label htmlFor="tasks-path">
              Tasks path
              <input id="tasks-path" value={loaded.editable.tasks_path} readOnly />
            </label>
            <label htmlFor="output-dir">
              Output dir
              <input id="output-dir" value={loaded.editable.output_dir || './runs'} readOnly />
            </label>
          </div>
          <div className="button-row">
            <button type="button" onClick={() => guarded(() => loadConfig())}>
              Load config
            </button>
            <button type="button" onClick={() => guarded(saveConfig)} disabled={serverMode !== 'connected'}>
              Save config
            </button>
          </div>
          <p className="status-line" data-testid="save-status">
            {saveStatus}
          </p>
        </section>

        <section className="panel matrix-panel">
          <div className="panel-heading">
            <h2>Run Matrix</h2>
            <span data-testid="matrix-count">{visibleCaseCount}</span>
          </div>
          <dl className="metric-grid">
            <div>
              <dt>Agents</dt>
              <dd>{agents.length}</dd>
            </div>
            <div>
              <dt>Tasks</dt>
              <dd>{loaded.editable.tasks.length}</dd>
            </div>
            <div>
              <dt>Variants</dt>
              <dd>{loaded.editable.variants.length}</dd>
            </div>
            <div>
              <dt>Trials</dt>
              <dd>{plan?.trials ?? localAppFixture.trials}</dd>
            </div>
          </dl>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Agent Profiles</h2>
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
            <h2>Tasks And Variants</h2>
          </div>
          <div className="two-column-list">
            <ul>
              {loaded.editable.tasks.map((task) => (
                <li key={task.id}>
                  <strong>{task.id}</strong>
                  <span>{task.title || task.prompt}</span>
                </li>
              ))}
            </ul>
            <ul>
              {loaded.editable.variants.map((variant) => (
                <li key={variant.name}>
                  <strong>{variant.name}</strong>
                  <span>{variant.description || 'Variant'}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="panel yaml-panel">
          <div className="panel-heading">
            <h2>Config Files</h2>
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
            <h2>Evaluation Criteria</h2>
          </div>
          <ul className="command-list">
            {(loaded.editable.evaluation_commands.length > 0
              ? loaded.editable.evaluation_commands
              : splitLines(configYaml).filter((line) => line.includes('pytest'))
            ).map((command) => (
              <li key={command}>
                <code>{command}</code>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Preflight And Run</h2>
          </div>
          <label htmlFor="cleanup-policy">
            Cleanup policy
            <select
              id="cleanup-policy"
              value={cleanupPolicy}
              onChange={(event) => setCleanupPolicy(event.target.value)}
            >
              <option value="never">never</option>
              <option value="always">always</option>
              <option value="successful">successful</option>
              <option value="failed">failed</option>
            </select>
          </label>
          <div className="button-row">
            <button type="button" onClick={() => guarded(runPreflight)} disabled={serverMode !== 'connected'}>
              Run preflight
            </button>
            <button type="button" onClick={() => guarded(planRun)} disabled={serverMode !== 'connected'}>
              Plan run
            </button>
            <button type="button" onClick={() => guarded(startRun)} disabled={serverMode !== 'connected'}>
              Start run
            </button>
            <button type="button" className="secondary" onClick={() => guarded(stopRun)} disabled={!run}>
              Stop
            </button>
          </div>
          <p className="status-line" data-testid="preflight-status">
            {preflightStatus}
          </p>
          <p className="status-line">
            Planned cases: <strong data-testid="planned-case-count">{plan?.case_count ?? 0}</strong>
          </p>
          <ul className="check-list">
            {preflightChecks.map((check) => (
              <li key={check}>{check}</li>
            ))}
          </ul>
        </section>

        <section className="panel run-panel">
          <div className="panel-heading">
            <h2>Run Progress</h2>
          </div>
          <p className="run-status" data-testid="run-status">
            {run ? `${run.status} ${run.completed_cases}/${run.case_count}` : 'Idle'}
          </p>
          <div className="log-box">
            {(logs?.console || []).map((line) => (
              <code key={line}>{line}</code>
            ))}
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
            <h2>Results And Exports</h2>
            <span>{results?.overview.case_count ?? 0}</span>
          </div>
          {results && (
            <>
              <dl className="metric-grid">
                <div>
                  <dt>Failed</dt>
                  <dd>{results.overview.failed_count}</dd>
                </div>
                <div>
                  <dt>Timeouts</dt>
                  <dd>{results.overview.timeout_count}</dd>
                </div>
                <div>
                  <dt>Low confidence</dt>
                  <dd>{results.overview.low_confidence_count}</dd>
                </div>
                <div>
                  <dt>Telemetry gaps</dt>
                  <dd>{results.overview.telemetry_gap_count}</dd>
                </div>
              </dl>
              <table>
                <thead>
                  <tr>
                    <th>Case</th>
                    <th>Agent</th>
                    <th>Status</th>
                    <th>Validation</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {results.cases.map((result) => (
                    <tr key={result.case_id}>
                      <td>{result.task_id}</td>
                      <td>{result.agent_name}</td>
                      <td>{result.status}</td>
                      <td>{result.validation_status}</td>
                      <td>{result.confidence}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
          <div className="button-row">
            <button type="button" onClick={() => guarded(() => exportRun('json'))} disabled={!run?.run_dir}>
              Export JSON
            </button>
            <button type="button" onClick={() => guarded(() => exportRun('csv'))} disabled={!run?.run_dir}>
              Export CSV
            </button>
            <button type="button" onClick={() => guarded(() => exportRun('markdown'))} disabled={!run?.run_dir}>
              Export Markdown
            </button>
            <button type="button" onClick={() => guarded(() => exportRun('html'))} disabled={!run?.run_dir}>
              Export HTML
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
