import { useEffect, useMemo, useRef, useState } from 'react';
import { apiRequest } from './api';
import { FirstRunPanel } from './components/FirstRunPanel';
import { RunPlanPanel } from './components/RunPlanPanel';
import { TaskEditor } from './components/TaskEditor';
import { WorkflowBand } from './components/WorkflowBand';
import { localAppFixture, plannedCaseCount } from './fixture';
import { agentsFrom, emptyConfig, fallbackConfig, listText, primaryAgent } from './localConfig';
import type {
  BootstrapResponse,
  CaseDetailPayload,
  EditableConfig,
  EditableTask,
  LoadedConfig,
  LogPayload,
  ManualReview,
  ResultsPayload,
  RunPlan,
  RunStatus,
  SaveResponse,
  WorkspaceState,
} from './types';
import './styles.css';

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

function validateEditableConfig(editable: EditableConfig) {
  const issues: string[] = [];
  const ids = editable.tasks.map((task) => task.id.trim());
  const duplicates = [...new Set(ids.filter((id, index) => id && ids.indexOf(id) !== index))];
  editable.tasks.forEach((task, index) => {
    const label = task.id.trim() || `第 ${index + 1} 个 task`;
    if (!task.id.trim()) {
      issues.push(`${label}: task id 不能为空`);
    }
    if (!task.prompt.trim()) {
      issues.push(`${label}: prompt 不能为空`);
    }
    task.validation_commands.forEach((command, commandIndex) => {
      if (!command.trim()) {
        issues.push(`${label}: validation command ${commandIndex + 1} 不能为空`);
      }
    });
    task.hard_evaluation?.command_checks?.forEach((check, checkIndex) => {
      if (!check.label.trim()) {
        issues.push(`${label}: command check ${checkIndex + 1} label 不能为空`);
      }
      if (!check.command.trim()) {
        issues.push(`${label}: command check ${checkIndex + 1} command 不能为空`);
      }
    });
    task.soft_evaluation?.rubric?.forEach((item, rubricIndex) => {
      if (!item.name.trim()) {
        issues.push(`${label}: rubric ${rubricIndex + 1} name 不能为空`);
      }
      if (!(item.weight > 0)) {
        issues.push(`${label}: rubric ${rubricIndex + 1} weight 必须大于 0`);
      }
    });
  });
  duplicates.forEach((id) => issues.push(`重复 task id: ${id}`));
  return issues;
}

function uniqueTaskId(base: string, tasks: EditableTask[]) {
  const used = new Set(tasks.map((task) => task.id));
  if (!used.has(base)) return base;
  let suffix = 2;
  while (used.has(`${base}-${suffix}`)) {
    suffix += 1;
  }
  return `${base}-${suffix}`;
}

function blankTask(tasks: EditableTask[]): EditableTask {
  return {
    id: uniqueTaskId('new-task', tasks),
    title: 'New evaluation task',
    prompt: '',
    category: 'bugfix',
    difficulty: 'easy',
    validation_commands: [],
    expected_outcome: {
      summary: '',
      acceptance_points: [],
      files: [],
    },
    hard_evaluation: {
      enabled: true,
      require_validation_pass: false,
      required_paths: [],
      forbidden_paths: [],
      expected_snippets: [],
      forbidden_snippets: [],
      command_checks: [],
    },
    soft_evaluation: {
      enabled: true,
      mode: 'payload-only',
      max_score: 10,
      rubric: [],
    },
  };
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
  const [taskValidationErrors, setTaskValidationErrors] = useState<string[]>([]);
  const [selectedTaskIndex, setSelectedTaskIndex] = useState(0);
  const [cleanupPolicy, setCleanupPolicy] = useState('successful');
  const [workspaceState, setWorkspaceState] = useState<WorkspaceState | null>(null);
  const [projectRepoPath, setProjectRepoPath] = useState('');
  const [configLoaded, setConfigLoaded] = useState(false);

  const fixtureCaseCount = useMemo(() => plannedCaseCount(localAppFixture), []);
  const agents = agentsFrom(loaded);
  const cocoAgent = primaryAgent(loaded);
  const task = loaded.editable.tasks[selectedTaskIndex] || loaded.editable.tasks[0];
  const estimatedCaseCount =
    agents.length * loaded.editable.tasks.length * loaded.editable.variants.length;
  const visibleCaseCount = plan?.case_count ?? (serverMode === 'fixture' ? fixtureCaseCount : estimatedCaseCount);

  function applyLoadedConfig(payload: LoadedConfig) {
    setLoaded(payload);
    setConfigPath(payload.config_path);
    setConfigYaml(payload.config_yaml);
    setTasksYaml(payload.tasks_yaml);
    setTaskValidationErrors([]);
    setSelectedTaskIndex((current) => Math.min(current, Math.max(payload.editable.tasks.length - 1, 0)));
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

  async function saveEditableConfig() {
    setError('');
    const issues = validateEditableConfig(loaded.editable);
    setTaskValidationErrors(issues);
    if (issues.length > 0) {
      return;
    }
    const saved = await apiRequest<SaveResponse>('/api/config/save-editable', {
      method: 'POST',
      body: JSON.stringify({
        config_path: loaded.config_path || configPath,
        tasks_path: loaded.tasks_path || loaded.editable.tasks_path || 'tasks.yaml',
        editable: loaded.editable,
      }),
    });
    if (saved.reloaded) {
      applyLoadedConfig(saved.reloaded);
      await planRun(saved.reloaded.config_path);
    } else {
      await loadConfig(saved.config_path);
      await planRun(saved.config_path);
    }
    setSaveStatus(`已保存任务并刷新 run plan: ${saved.tasks_path}`);
  }

  function updateEditable(updater: (editable: EditableConfig) => EditableConfig) {
    setLoaded((current) => ({
      ...current,
      editable: updater(current.editable),
    }));
    setPlan(null);
    setTaskValidationErrors([]);
  }

  function updateTask(index: number, taskPatch: EditableTask) {
    updateEditable((editable) => ({
      ...editable,
      tasks: editable.tasks.map((taskItem, taskIndex) => (
        taskIndex === index ? taskPatch : taskItem
      )),
    }));
  }

  function addTask() {
    updateEditable((editable) => ({ ...editable, tasks: [...editable.tasks, blankTask(editable.tasks)] }));
    setSelectedTaskIndex(loaded.editable.tasks.length);
  }

  function duplicateTask(index: number) {
    const source = loaded.editable.tasks[index];
    if (!source) return;
    const duplicate = {
      ...structuredClone(source),
      id: uniqueTaskId(`${source.id || 'task'}-copy`, loaded.editable.tasks),
      title: source.title ? `${source.title} copy` : 'Copied evaluation task',
    };
    updateEditable((editable) => ({ ...editable, tasks: [...editable.tasks, duplicate] }));
    setSelectedTaskIndex(loaded.editable.tasks.length);
  }

  function deleteTask(index: number) {
    const source = loaded.editable.tasks[index];
    if (!source || loaded.editable.tasks.length <= 1) return;
    const confirmed = window.confirm(`删除 task "${source.id}"？`);
    if (!confirmed) return;
    updateEditable((editable) => ({
      ...editable,
      tasks: editable.tasks.filter((_, taskIndex) => taskIndex !== index),
    }));
    setSelectedTaskIndex(Math.max(0, index - 1));
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

  async function planRun(path = loaded.config_path || configPath) {
    const payload = await apiRequest<RunPlan>('/api/run-plan', {
      method: 'POST',
      body: JSON.stringify({
        config_path: path,
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
    if (selectedTaskIndex >= loaded.editable.tasks.length) {
      setSelectedTaskIndex(Math.max(loaded.editable.tasks.length - 1, 0));
    }
  }, [loaded.editable.tasks.length, selectedTaskIndex]);

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

      <WorkflowBand
        steps={[
          ['Project', loaded.resolved.repo_path],
          ['Agent', cocoAgent?.name || '未配置'],
          ['Preflight', preflightStepLabel],
          ['Run', runLabel],
          ['Results', results ? '已加载' : '本地'],
        ]}
      />

      {isFirstRun && (
        <FirstRunPanel
          projectRepoPath={projectRepoPath}
          onProjectRepoPathChange={setProjectRepoPath}
          onBootstrapDemo={() => guarded(bootstrapDemo)}
          onInitializeProject={() => guarded(initializeProject)}
        />
      )}

      {!isFirstRun && (
      <section className="content-grid">
        <RunPlanPanel
          agents={agents}
          taskCount={loaded.editable.tasks.length}
          variants={loaded.editable.variants}
          visibleCaseCount={visibleCaseCount}
          plan={plan}
          defaultTrials={localAppFixture.trials}
        />
        <TaskEditor
          tasks={loaded.editable.tasks}
          variants={loaded.editable.variants}
          selectedTaskIndex={selectedTaskIndex}
          saveStatus={saveStatus}
          serverMode={serverMode}
          validationErrors={taskValidationErrors}
          onSelectTask={setSelectedTaskIndex}
          onUpdateTask={updateTask}
          onAddTask={addTask}
          onDuplicateTask={duplicateTask}
          onDeleteTask={deleteTask}
          onSave={() => guarded(saveEditableConfig)}
        />
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
