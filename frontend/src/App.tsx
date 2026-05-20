import { useEffect, useMemo, useRef, useState } from 'react';
import { apiRequest } from './api';
import { AdvancedConfigDetails } from './components/AdvancedConfigDetails';
import { AgentEditor } from './components/AgentEditor';
import { FirstRunPanel } from './components/FirstRunPanel';
import { RunPlanPanel } from './components/RunPlanPanel';
import { RunControls } from './components/RunControls';
import { TaskEditor } from './components/TaskEditor';
import { VariantEditor } from './components/VariantEditor';
import { WorkflowBand } from './components/WorkflowBand';
import { localAppFixture, plannedCaseCount } from './fixture';
import {
  agentsFrom,
  availableScope,
  blankTask,
  emptyConfig,
  emptyRunScope,
  fallbackConfig,
  primaryAgent,
  reconcileRunScope,
  uniqueTaskId,
  validateEditableConfig,
} from './localConfig';
import type {
  BootstrapResponse,
  CaseDetailPayload,
  CompareGroup,
  EditableAgent,
  EditableConfig,
  EditableTask,
  EditableVariant,
  HardEvaluationPayload,
  LoadedConfig,
  LogPayload,
  ManualReview,
  ResultCase,
  ResultsPayload,
  RunPlan,
  RunScope,
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

const evaluationLabels: Record<string, string> = {
  passed: '通过',
  failed: '失败',
  skipped: '跳过',
  payload_generated: '已生成待复核材料',
  not_configured: '未配置',
};

const telemetryLabels: Record<string, string> = {
  collected: '已采集',
  partial: '部分采集',
  error: '采集错误',
  unavailable: '不可用',
};

const telemetryEvidenceGapLabels: Record<string, string> = {
  codex_events_missing: 'Codex JSONL events 缺失',
  codex_events_empty: 'Codex JSONL events 为空',
  codex_events_malformed: 'Codex JSONL events 格式错误',
  codex_usage_missing: 'Codex usage 缺失',
  codex_model_missing: 'Codex 模型信息缺失',
  codex_final_message_missing: 'Codex final message 缺失',
  codex_output_last_message_missing: 'Codex --output-last-message 文件缺失，已从 JSONL 恢复',
};

const reviewDecisionLabels: Record<string, string> = {
  not_reviewed: '未复核',
  pass: '通过',
  fail: '失败',
  needs_review: '需要复核',
};

const confidenceLabels: Record<string, string> = {
  unknown: '未知',
  low: '低',
  medium: '中',
  high: '高',
};

const compareVerdictLabels: Record<string, string> = {
  comparison_improved: '对比对象改善',
  comparison_regressed: '对比对象回退',
  evidence_limited: '证据不足',
  no_clear_change: '无明确变化',
};

const baselineStorageKey = 'context-eval.compareBaselineVariant';

function labelFor(labels: Record<string, string>, value: string | undefined | null) {
  if (!value) return '未知';
  return labels[value] ?? value;
}

function storedBaselineVariant() {
  if (typeof window === 'undefined') return '';
  try {
    return window.localStorage.getItem(baselineStorageKey) || '';
  } catch {
    return '';
  }
}

function rememberBaselineVariant(value: string) {
  if (typeof window === 'undefined') return;
  try {
    if (value) {
      window.localStorage.setItem(baselineStorageKey, value);
    } else {
      window.localStorage.removeItem(baselineStorageKey);
    }
  } catch {
    // localStorage can be unavailable in restricted browser contexts.
  }
}

function signedDelta(value: number | null | undefined) {
  if (value === null || value === undefined) return '-';
  return value > 0 ? `+${value}` : String(value);
}

function metricValue(value: number | string | null | undefined, suffix = '') {
  if (value === null || value === undefined || value === '') return '-';
  return `${value}${suffix}`;
}

function isCodexUsageCase(result: ResultCase | undefined | null) {
  if (!result) return false;
  return (
    result.telemetry_source === 'codex-jsonl' ||
    Boolean(result.codex_events_path) ||
    Boolean(result.codex_final_message_path) ||
    Boolean(result.telemetry_evidence_gaps?.length)
  );
}

function evidenceGapText(code: string) {
  return telemetryEvidenceGapLabels[code] || code;
}

function resultVariants(results: ResultsPayload | null) {
  return results?.available_baseline_variants?.length
    ? results.available_baseline_variants
    : Array.from(new Set((results?.cases || []).map((item) => item.variant))).sort();
}

function confidenceReason(value: string | undefined | null) {
  if (value === 'high') return '已配置 validation commands，且全部通过。';
  if (value === 'medium') return 'validation commands 存在，但至少一个失败或超时。';
  if (value === 'low') return '没有可用 validation commands，不能给高置信判断。';
  return '缺少可信度信息。';
}

function caseEvidenceNotes(result: ResultCase) {
  const notes: { title: string; message: string; nextStep: string }[] = [];
  if (result.validation_status === 'skipped') {
    notes.push({
      title: '无 validation',
      message: '本用例没有运行项目验证命令，patch 和日志只能作为人工复核材料。',
      nextStep: '为任务配置项目自己的测试或验证脚本后重新运行。',
    });
  }
  if (result.hard_evaluation_status === 'skipped') {
    notes.push({
      title: 'hard check skipped',
      message: '硬性检查缺少可评分本地产物，不能把缺失证据当作通过。',
      nextStep: '保留工作区，或补充可从 patch 判断的 hard_evaluation 规则。',
    });
  }
  if (result.hard_evaluation_status === 'not_configured') {
    notes.push({
      title: '未配置 hard evaluation',
      message: '当前没有 deterministic hard checks，不能读成综合质量分。',
      nextStep: '添加 required paths、snippet checks 或 command checks。',
    });
  }
  if ((result.telemetry_status || 'unavailable') !== 'collected') {
    notes.push({
      title: 'telemetry missing',
      message: result.telemetry_error || '没有结构化 telemetry，token、耗时和工具调用保持未知。',
      nextStep: '确认 agent 是否写入本地 telemetry JSON；不要从日志猜测。',
    });
  }
  (result.telemetry_evidence_gaps || []).forEach((gap) => {
    notes.push({
      title: 'Codex evidence gap',
      message: evidenceGapText(gap),
      nextStep: '检查 case-local Codex JSONL、final message 和 stdout/stderr artifact；不要从非结构化日志猜测关键指标。',
    });
  });
  return notes;
}

function hardEvaluationFrom(caseDetail: CaseDetailPayload | null): HardEvaluationPayload | null {
  return caseDetail?.hard_evaluation || caseDetail?.case.hard_evaluation || null;
}

export function App() {
  const resultsPanelRef = useRef<HTMLElement | null>(null);
  const shouldRevealResultsRef = useRef(false);
  const runScopeRef = useRef<RunScope>(emptyRunScope());
  const availableScopeRef = useRef<RunScope>(emptyRunScope());
  const scopeInitializedRef = useRef(false);
  const [serverMode, setServerMode] = useState<'checking' | 'connected' | 'fixture'>('checking');
  const [configPath, setConfigPath] = useState('context-eval.yaml');
  const [loaded, setLoaded] = useState<LoadedConfig>(() => emptyConfig());
  const loadedRef = useRef<LoadedConfig>(loaded);
  const [configYaml, setConfigYaml] = useState('');
  const [tasksYaml, setTasksYaml] = useState('');
  const [saveStatus, setSaveStatus] = useState('尚未保存');
  const [preflightStatus, setPreflightStatus] = useState('待检查');
  const [preflightChecks, setPreflightChecks] = useState<string[]>([]);
  const [plan, setPlan] = useState<RunPlan | null>(null);
  const [run, setRun] = useState<RunStatus | null>(null);
  const [logs, setLogs] = useState<LogPayload | null>(null);
  const [results, setResults] = useState<ResultsPayload | null>(null);
  const [compareBaselineVariant, setCompareBaselineVariant] = useState(storedBaselineVariant);
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
  const [selectedVariantIndex, setSelectedVariantIndex] = useState(0);
  const [selectedAgentIndex, setSelectedAgentIndex] = useState(0);
  const [runScope, setRunScope] = useState<RunScope>(() => emptyRunScope());
  const [scopeNotice, setScopeNotice] = useState('');
  const [cleanupPolicy, setCleanupPolicy] = useState('successful');
  const [workspaceState, setWorkspaceState] = useState<WorkspaceState | null>(null);
  const [projectRepoPath, setProjectRepoPath] = useState('');
  const [configLoaded, setConfigLoaded] = useState(false);

  const fixtureCaseCount = useMemo(() => plannedCaseCount(localAppFixture), []);
  const agents = agentsFrom(loaded);
  const cocoAgent = primaryAgent(loaded);
  const task = loaded.editable.tasks[selectedTaskIndex] || loaded.editable.tasks[0];
  const estimatedCaseCount = agents.length * loaded.editable.tasks.length * loaded.editable.variants.length;
  const selectedCaseCount = runScope.task_ids.length * runScope.variants.length * runScope.agents.length;
  const visibleCaseCount =
    plan?.case_count ?? (configLoaded ? selectedCaseCount : (serverMode === 'fixture' ? fixtureCaseCount : estimatedCaseCount));

  function applyLoadedConfig(payload: LoadedConfig) {
    const nextAvailable = availableScope(payload);
    const reconciled = reconcileRunScope(
      runScopeRef.current,
      availableScopeRef.current,
      nextAvailable,
      scopeInitializedRef.current,
    );
    runScopeRef.current = reconciled.scope;
    availableScopeRef.current = nextAvailable;
    scopeInitializedRef.current = true;
    setRunScope(reconciled.scope);
    setScopeNotice(reconciled.changed ? '运行范围已按最新配置自动清理，请确认本次选择。' : '');
    loadedRef.current = payload;
    setLoaded(payload);
    setConfigPath(payload.config_path);
    setConfigYaml(payload.config_yaml);
    setTasksYaml(payload.tasks_yaml);
    setTaskValidationErrors([]);
    setSelectedTaskIndex((current) => Math.min(current, Math.max(payload.editable.tasks.length - 1, 0)));
    setSelectedVariantIndex((current) => Math.min(current, Math.max(payload.editable.variants.length - 1, 0)));
    setSelectedAgentIndex((current) => Math.min(current, Math.max(agentsFrom(payload).length - 1, 0)));
    setConfigLoaded(true);
    setWorkspaceState((current) => ({
      state: 'configured',
      has_config: true,
      default_config_path: current?.default_config_path || payload.config_path,
      config_path: payload.config_path,
      workspace_root: current?.workspace_root,
    }));
    return reconciled.scope;
  }

  async function loadConfig(path = configPath) {
    setError('');
    if (serverMode === 'fixture') {
      const scope = applyLoadedConfig(fallbackConfig());
      setSaveStatus('示例配置已加载');
      return scope;
    }
    const payload = await apiRequest<LoadedConfig>('/api/config/load', {
      method: 'POST',
      body: JSON.stringify({ config_path: path }),
    });
    const scope = applyLoadedConfig(payload);
    setSaveStatus('已加载本地配置');
    return scope;
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

  async function saveEditableConfig(message = '已保存配置并刷新执行计划') {
    setError('');
    const currentLoaded = loadedRef.current;
    const issues = validateEditableConfig(currentLoaded.editable);
    setTaskValidationErrors(issues);
    if (issues.length > 0) {
      return;
    }
    const saved = await apiRequest<SaveResponse>('/api/config/save-editable', {
      method: 'POST',
      body: JSON.stringify({
        config_path: currentLoaded.config_path || configPath,
        tasks_path: currentLoaded.tasks_path || currentLoaded.editable.tasks_path || 'tasks.yaml',
        editable: currentLoaded.editable,
      }),
    });
    let nextScope = runScopeRef.current;
    if (saved.reloaded) {
      nextScope = applyLoadedConfig(saved.reloaded);
      await planRun(saved.reloaded.config_path, nextScope);
    } else {
      nextScope = await loadConfig(saved.config_path);
      await planRun(saved.config_path, nextScope);
    }
    setSaveStatus(`${message}: ${saved.config_path} / ${saved.tasks_path}`);
  }

  function updateEditable(updater: (editable: EditableConfig) => EditableConfig) {
    const nextLoaded = {
      ...loadedRef.current,
      editable: updater(loadedRef.current.editable),
    };
    loadedRef.current = nextLoaded;
    setLoaded(nextLoaded);
    setPlan(null);
  }

  function commitRunScope(nextScope: RunScope) {
    runScopeRef.current = nextScope;
    setRunScope(nextScope);
    setPlan(null);
  }

  function toggleRunScope(kind: keyof RunScope, value: string, checked: boolean) {
    const current = runScopeRef.current;
    const selected = current[kind];
    const nextValues = checked
      ? [...selected, value]
      : selected.filter((item) => item !== value);
    setScopeNotice('');
    commitRunScope({ ...current, [kind]: nextValues });
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
      title: source.title ? `${source.title} 副本` : '复制的评测任务',
    };
    updateEditable((editable) => ({ ...editable, tasks: [...editable.tasks, duplicate] }));
    setSelectedTaskIndex(loaded.editable.tasks.length);
  }

  function deleteTask(index: number) {
    const source = loaded.editable.tasks[index];
    if (!source || loaded.editable.tasks.length <= 1) return;
    const confirmed = window.confirm(`删除任务 "${source.id}"？`);
    if (!confirmed) return;
    updateEditable((editable) => ({
      ...editable,
      tasks: editable.tasks.filter((_, taskIndex) => taskIndex !== index),
    }));
    setSelectedTaskIndex(Math.max(0, index - 1));
  }

  function syncAgents(editable: EditableConfig, profiles: EditableAgent[]) {
    const nextProfiles = profiles.length > 0
      ? profiles
      : [{
          name: 'new-agent',
          kind: 'custom',
          command: '',
          timeout_minutes: 60,
          network: 'disabled',
        }];
    return {
      ...editable,
      agent: nextProfiles[0],
      agents: nextProfiles,
      agent_shape: editable.agent_shape === 'agents' || nextProfiles.length > 1 ? 'agents' : 'agent',
    };
  }

  function updateAgents(profiles: EditableAgent[]) {
    updateEditable((editable) => syncAgents(editable, profiles));
  }

  function updateVariants(variants: EditableVariant[]) {
    updateEditable((editable) => ({ ...editable, variants }));
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
    setSaveStatus('真实项目配置已创建，请检查执行器命令和评测任务');
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

  function runRequestBody(path = loaded.config_path || configPath, scope = runScopeRef.current) {
    return {
      config_path: path,
      cleanup_policy: cleanupPolicy,
      task_ids: scope.task_ids,
      variants: scope.variants,
      agents: scope.agents,
    };
  }

  async function planRun(path = loaded.config_path || configPath, scope = runScopeRef.current) {
    const payload = await apiRequest<RunPlan>('/api/run-plan', {
      method: 'POST',
      body: JSON.stringify(runRequestBody(path, scope)),
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

  async function loadResults(runDir: string, baselineVariant = compareBaselineVariant) {
    const params = new URLSearchParams({ run_dir: runDir });
    if (baselineVariant) {
      params.set('baseline_variant', baselineVariant);
    }
    const resultPayload = await apiRequest<ResultsPayload>(`/api/results?${params.toString()}`);
    const resolvedBaseline = resultPayload.selected_baseline_variant || '';
    setCompareBaselineVariant(resolvedBaseline);
    rememberBaselineVariant(resolvedBaseline);
    setResults(resultPayload);
    if (selectedCaseId && !resultPayload.cases.some((item) => item.case_id === selectedCaseId)) {
      setSelectedCaseId('');
      setCaseDetail(null);
    }
  }

  async function changeCompareBaseline(value: string) {
    setError('');
    setCompareBaselineVariant(value);
    rememberBaselineVariant(value);
    if (run?.run_dir) {
      await loadResults(run.run_dir, value);
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
    setReviewStatus('复核已保存');
  }

  async function refreshRunStatus(appRunId: string) {
    const status = await apiRequest<RunStatus>(`/api/runs/${appRunId}`);
    setRun(status);
    await loadResultsForRun(status);
    return status;
  }

  async function startRun() {
    setError('');
    const scope = runScopeRef.current;
    if (scope.task_ids.length === 0 || scope.variants.length === 0 || scope.agents.length === 0) {
      throw new Error('请至少选择一个任务、上下文版本和执行器');
    }
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
      await planRun(loaded.config_path || configPath, scope);
      const payload = await apiRequest<RunStatus>('/api/runs', {
        method: 'POST',
        body: JSON.stringify({
          ...runRequestBody(loaded.config_path || configPath, scope),
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
          const empty = emptyConfig();
          loadedRef.current = empty;
          setLoaded(empty);
          setConfigYaml('');
          setTasksYaml('');
          runScopeRef.current = emptyRunScope();
          availableScopeRef.current = emptyRunScope();
          scopeInitializedRef.current = false;
          setRunScope(emptyRunScope());
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
    if (selectedVariantIndex >= loaded.editable.variants.length) {
      setSelectedVariantIndex(Math.max(loaded.editable.variants.length - 1, 0));
    }
  }, [loaded.editable.variants.length, selectedVariantIndex]);

  useEffect(() => {
    if (selectedAgentIndex >= agents.length) {
      setSelectedAgentIndex(Math.max(agents.length - 1, 0));
    }
  }, [agents.length, selectedAgentIndex]);

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
  const variantSummary = runScope.variants.join(' vs ') || '未选择上下文版本';
  const agentSummary = runScope.agents.join(', ') || cocoAgent?.name || '未配置执行器';
  const runBrief = configLoaded
    ? `用 ${agentSummary} 在 ${variantSummary} 上执行 ${runScope.task_ids.length} 个任务，预计 ${visibleCaseCount} 个评测用例。`
    : '先试用示例或打开一个本地 Git 项目。';
  const availableBaselineVariants = resultVariants(results);
  const selectedBaselineValue =
    compareBaselineVariant || results?.selected_baseline_variant || availableBaselineVariants[0] || '';
  const evaluationExplanation = results?.evaluation_explanation;
  const detailHardEvaluation = hardEvaluationFrom(caseDetail);
  const detailEvidenceNotes = caseDetail ? caseEvidenceNotes(caseDetail.case) : [];

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
          ['项目', loaded.resolved.repo_path],
          ['执行器', cocoAgent?.name || '未配置'],
          ['运行检查', preflightStepLabel],
          ['运行', runLabel],
          ['结果', results ? '已加载' : '本地'],
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
          runScope={runScope}
        />
        {(taskValidationErrors.length > 0 || scopeNotice) && (
          <div className="notice validation-notice scope-notice" role="alert">
            {scopeNotice && <div>{scopeNotice}</div>}
            {taskValidationErrors.map((issue) => (
              <div key={issue}>{issue}</div>
            ))}
          </div>
        )}
        <VariantEditor
          variants={loaded.editable.variants}
          selectedVariantIndex={selectedVariantIndex}
          saveStatus={saveStatus}
          serverMode={serverMode}
          onSelectVariant={setSelectedVariantIndex}
          onUpdateVariants={updateVariants}
          onSave={() => guarded(() => saveEditableConfig('已保存配置并刷新执行计划'))}
        />
        <AgentEditor
          agents={agents}
          selectedAgentIndex={selectedAgentIndex}
          saveStatus={saveStatus}
          serverMode={serverMode}
          onSelectAgent={setSelectedAgentIndex}
          onUpdateAgents={updateAgents}
          onSave={() => guarded(() => saveEditableConfig('已保存配置并刷新执行计划'))}
        />
        <TaskEditor
          tasks={loaded.editable.tasks}
          variants={loaded.editable.variants}
          selectedTaskIndex={selectedTaskIndex}
          saveStatus={saveStatus}
          serverMode={serverMode}
          validationErrors={[]}
          onSelectTask={setSelectedTaskIndex}
          onUpdateTask={updateTask}
          onAddTask={addTask}
          onDuplicateTask={duplicateTask}
          onDeleteTask={deleteTask}
          onSave={() => guarded(() => saveEditableConfig('已保存任务并刷新执行计划'))}
        />
        <AdvancedConfigDetails
          agents={agents}
          configPath={configPath}
          configYaml={configYaml}
          loaded={loaded}
          modeLabel={modeLabel}
          saveStatus={saveStatus}
          serverMode={serverMode}
          task={task}
          tasksYaml={tasksYaml}
          onConfigPathChange={setConfigPath}
          onConfigYamlChange={setConfigYaml}
          onLoadConfig={() => guarded(async () => { await loadConfig(); })}
          onSaveConfig={() => guarded(saveConfig)}
          onTasksYamlChange={setTasksYaml}
        />

        <RunControls
          cleanupPolicy={cleanupPolicy}
          isRunActive={isRunActive}
          plan={plan}
          preflightChecks={preflightChecks}
          preflightStatus={preflightStatus}
          resultSummary={resultSummary}
          results={results}
          runBrief={runBrief}
          runScope={runScope}
          selectedCaseCount={visibleCaseCount}
          serverMode={serverMode}
          taskSummary={task?.expected_outcome?.summary || '未配置期望结果摘要'}
          taskTitle={taskTitle}
          tasks={loaded.editable.tasks}
          variants={loaded.editable.variants}
          agents={agents}
          onCleanupPolicyChange={setCleanupPolicy}
          onPlan={() => guarded(async () => { await planRun(); })}
          onRevealResults={() => resultsPanelRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })}
          onStart={() => guarded(startRun)}
          onStop={() => guarded(stopRun)}
          onToggleScope={toggleRunScope}
          labelForCheck={(check) => labelFor(checkLabels, check)}
        />

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
            <h2>评测结果</h2>
            <span>{results?.overview.case_count ?? 0}</span>
          </div>
          {results ? (
            <>
              <div className="evaluation-guide" aria-label="评分依据">
                <div className="guide-heading">
                  <strong>评分依据</strong>
                  <span>{evaluationExplanation?.local_only || '仅基于本地产物观察，不是公开 benchmark 或 agent 排行。'}</span>
                </div>
                <div className="guide-grid">
                  <article className="guide-card">
                    <strong>Validation confidence</strong>
                    <dl>
                      <div>
                        <dt>高</dt>
                        <dd>
                          {evaluationExplanation?.validation_confidence.high ||
                            '配置了 validation commands，且验证通过。'}
                        </dd>
                      </div>
                      <div>
                        <dt>中</dt>
                        <dd>
                          {evaluationExplanation?.validation_confidence.medium ||
                            '配置了 validation commands，但验证失败或超时。'}
                        </dd>
                      </div>
                      <div>
                        <dt>低</dt>
                        <dd>
                          {evaluationExplanation?.validation_confidence.low ||
                            '没有 validation commands，不能做高置信判断。'}
                        </dd>
                      </div>
                    </dl>
                  </article>
                  <article className="guide-card">
                    <strong>Hard evaluation</strong>
                    <p>
                      {evaluationExplanation?.hard_evaluation.score_meaning ||
                        'hard score 是通过检查数 / 可评分检查数，不是综合质量分。'}
                    </p>
                    <p>
                      {evaluationExplanation?.hard_evaluation.skipped_meaning ||
                        'skipped 表示本地产物不足，不能把缺失证据当作通过。'}
                    </p>
                  </article>
                  <article className="guide-card">
                    <strong>Soft evaluation</strong>
                    <p>
                      {evaluationExplanation?.soft_evaluation.meaning ||
                        '当前只生成 payload-only 复核材料，不自动调用 OpenAI、Claude 或其他 LLM judge。'}
                    </p>
                  </article>
                  <article className="guide-card">
                    <strong>Manual review</strong>
                    <p>
                      {evaluationExplanation?.manual_review.meaning ||
                        '人工复核保存的是 reviewer 的证据和结论，不是自动评分。'}
                    </p>
                  </article>
                </div>
                <ul className="evidence-limit-list">
                  {(evaluationExplanation?.evidence_limits || [
                    '无 validation、hard check skipped 或 telemetry missing 时，只能提示证据不足和下一步。',
                  ]).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <dl className="metric-grid">
                <div>
                  <dt>失败用例</dt>
                  <dd>{results.overview.failed_count}</dd>
                </div>
                <div>
                  <dt>超时</dt>
                  <dd>{results.overview.timeout_count}</dd>
                </div>
                <div>
                  <dt>低可信度</dt>
                  <dd>{results.overview.low_confidence_count}</dd>
                </div>
                <div>
                  <dt>遥测缺口</dt>
                  <dd>{results.overview.telemetry_gap_count}</dd>
                </div>
              </dl>
              {availableBaselineVariants.length > 0 && (
                <section className="compare-summary" aria-label="对比摘要">
                  <div className="panel-heading compact-heading">
                    <h3>对比摘要</h3>
                    <span>{results.compare_groups?.length ?? 0}</span>
                  </div>
                  <div className="baseline-control">
                    <label htmlFor="compare-baseline">
                      比较基线
                      <select
                        id="compare-baseline"
                        aria-label="比较基线"
                        value={selectedBaselineValue}
                        onChange={(event) => {
                          const nextBaseline = event.target.value;
                          void guarded(() => changeCompareBaseline(nextBaseline));
                        }}
                      >
                        {availableBaselineVariants.map((variant) => (
                          <option key={variant} value={variant}>
                            {variant}
                          </option>
                        ))}
                      </select>
                    </label>
                    <p className="status-line">除当前基线外的上下文版本会与当前基线比较。</p>
                  </div>
                  {results.baseline_selection_notice && (
                    <div className="notice validation-notice">{results.baseline_selection_notice}</div>
                  )}
                  {(results.compare_groups || []).length > 0 ? (
                    <div className="compare-grid">
                      {(results.compare_groups || []).map((group: CompareGroup) => (
                        <article className="compare-card" key={group.group_id}>
                          <div className="compare-card-heading">
                            <strong>{labelFor(compareVerdictLabels, group.verdict)}</strong>
                            <span>{group.summary}</span>
                          </div>
                          <dl>
                            <div>
                              <dt>任务</dt>
                              <dd>{group.task_id}</dd>
                            </div>
                            <div>
                              <dt>比较基线</dt>
                              <dd>{group.baseline_variant}</dd>
                            </div>
                            <div>
                              <dt>对比对象</dt>
                              <dd>{group.comparison_variant}</dd>
                            </div>
                            <div>
                              <dt>Validation delta</dt>
                              <dd>{signedDelta(group.validation_delta)}</dd>
                            </div>
                            <div>
                              <dt>Hard check delta</dt>
                              <dd>{signedDelta(group.hard_check_delta)}</dd>
                            </div>
                            <div>
                              <dt>令牌差值</dt>
                              <dd>{signedDelta(group.total_tokens_delta)}</dd>
                            </div>
                          </dl>
                          <div className="evidence-gap-block">
                            <strong>证据不足原因</strong>
                            {group.evidence_gaps.length > 0 ? (
                              <ul className="evidence-gap-list">
                                {group.evidence_gaps.map((gap) => (
                                  <li key={`${group.group_id}:${gap.code}:${gap.variant}`}>
                                    <span>{gap.message}</span>
                                    <small>{gap.next_step}</small>
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <small>未发现影响本次比较的证据缺口。</small>
                            )}
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <p className="status-line">当前基线没有可对比对象，至少选择两个 variant 后会生成摘要。</p>
                  )}
                </section>
              )}
              <table>
                <thead>
                  <tr>
                    <th>用例</th>
                    <th>执行器</th>
                    <th>状态</th>
                    <th>验证</th>
                    <th>可信度</th>
                    <th>遥测</th>
                    <th>令牌</th>
                    <th>工具</th>
                    <th>硬性检查</th>
                    <th>软性材料</th>
                    <th>复核</th>
                    <th>详情</th>
                  </tr>
                </thead>
                <tbody>
                  {results.cases.map((result) => {
                    const evidenceNotes = caseEvidenceNotes(result);
                    return (
                      <tr key={result.case_id} className={selectedCaseId === result.case_id ? 'selected-row' : ''}>
                        <td data-label="用例">
                          {result.task_id}
                          <small>{result.variant}</small>
                        </td>
                        <td data-label="执行器">{result.agent_name}</td>
                        <td data-label="状态">{labelFor(resultStatusLabels, result.status)}</td>
                        <td data-label="验证">{labelFor(validationLabels, result.validation_status)}</td>
                        <td data-label="可信度">
                          {labelFor(confidenceLabels, result.confidence)}
                          <small>{confidenceReason(result.confidence)}</small>
                        </td>
                        <td data-label="遥测">
                          {labelFor(telemetryLabels, result.telemetry_status || 'unavailable')}
                          {result.agent_duration_seconds != null && (
                            <small>{result.agent_duration_seconds.toFixed(1)}s</small>
                          )}
                          {result.telemetry_error && <small>{result.telemetry_error}</small>}
                        </td>
                        <td data-label="令牌">
                          {result.total_tokens ?? '-'}
                          {result.reasoning_tokens != null && <small>推理 {result.reasoning_tokens}</small>}
                        </td>
                        <td data-label="工具">
                          {result.tool_call_count ?? '-'}
                          {result.reasoning_step_count != null && <small>轮次 {result.reasoning_step_count}</small>}
                          {result.command_call_count != null && <small>命令 {result.command_call_count}</small>}
                          {result.model_name && <small>{result.model_name}</small>}
                        </td>
                        <td data-label="硬性检查">
                          {labelFor(evaluationLabels, result.hard_evaluation_status || 'not_configured')}{' '}
                          {result.hard_evaluation_score ?? '-'}
                          /
                          {result.hard_evaluation_max_score ?? '-'}
                          <small>通过检查数 / 可评分检查数</small>
                        </td>
                        <td data-label="软性材料">
                          {labelFor(evaluationLabels, result.soft_evaluation_status || 'not_configured')}
                          {result.soft_evaluation_payload_path && <small>payload-only</small>}
                        </td>
                        <td data-label="复核">
                          {labelFor(reviewDecisionLabels, result.manual_review?.decision || 'not_reviewed')}
                          {result.manual_review?.confidence && (
                            <small>{labelFor(confidenceLabels, result.manual_review.confidence)}</small>
                          )}
                        </td>
                        <td data-label="详情">
                          <button
                            type="button"
                            className="secondary compact-button"
                            onClick={() => guarded(() => loadCaseDetail(result.case_id))}
                          >
                            查看详情
                          </button>
                          {evidenceNotes.length > 0 && <small>有证据不足解释</small>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {caseDetail && (
                <section className="case-detail-panel">
                  <div className="panel-heading compact-heading">
                    <h3>用例详情</h3>
                    <span>{caseDetail.case.variant}</span>
                  </div>
                  <div className="detail-grid">
                    <dl className="compact-list">
                      <div>
                        <dt>用例 ID</dt>
                        <dd>{caseDetail.case.case_id}</dd>
                      </div>
                      <div>
                        <dt>状态</dt>
                        <dd>{labelFor(resultStatusLabels, caseDetail.case.status)}</dd>
                      </div>
                      <div>
                        <dt>验证</dt>
                        <dd>{labelFor(validationLabels, caseDetail.case.validation_status)}</dd>
                      </div>
                      <div>
                        <dt>可信度</dt>
                        <dd>
                          {labelFor(confidenceLabels, caseDetail.case.confidence)}
                          <small>{confidenceReason(caseDetail.case.confidence)}</small>
                        </dd>
                      </div>
                      <div>
                        <dt>遥测</dt>
                        <dd>
                          {labelFor(telemetryLabels, caseDetail.case.telemetry_status || 'unavailable')}
                          {caseDetail.case.telemetry_error && <small>{caseDetail.case.telemetry_error}</small>}
                        </dd>
                      </div>
                      <div>
                        <dt>硬性检查</dt>
                        <dd>
                          {labelFor(evaluationLabels, caseDetail.case.hard_evaluation_status)}{' '}
                          {caseDetail.case.hard_evaluation_score ?? '-'}/
                          {caseDetail.case.hard_evaluation_max_score ?? '-'}
                          <small>通过检查数 / 可评分检查数，不是综合质量分。</small>
                        </dd>
                      </div>
                      <div>
                        <dt>软性材料</dt>
                        <dd>
                          {labelFor(evaluationLabels, caseDetail.case.soft_evaluation_status || 'not_configured')}
                          {caseDetail.case.soft_evaluation_payload_path && <small>payload-only</small>}
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
                        复核结论
                        <select
                          id="review-decision"
                          aria-label="复核结论"
                          value={reviewDraft.decision}
                          onChange={(event) =>
                            setReviewDraft((current) => ({ ...current, decision: event.target.value }))
                          }
                        >
                          <option value="not_reviewed">未复核</option>
                          <option value="pass">通过</option>
                          <option value="fail">失败</option>
                          <option value="needs_review">需要复核</option>
                        </select>
                      </label>
                      <label htmlFor="review-confidence">
                        可信度
                        <select
                          id="review-confidence"
                          aria-label="复核可信度"
                          value={reviewDraft.confidence}
                          onChange={(event) =>
                            setReviewDraft((current) => ({ ...current, confidence: event.target.value }))
                          }
                        >
                          <option value="unknown">未知</option>
                          <option value="low">低</option>
                          <option value="medium">中</option>
                          <option value="high">高</option>
                        </select>
                      </label>
                      <label htmlFor="reviewer">
                        复核人
                        <input
                          id="reviewer"
                          aria-label="复核人"
                          value={reviewDraft.reviewer}
                          onChange={(event) =>
                            setReviewDraft((current) => ({ ...current, reviewer: event.target.value }))
                          }
                        />
                      </label>
                      <label htmlFor="review-notes">
                        备注
                        <textarea
                          id="review-notes"
                          aria-label="复核备注"
                          value={reviewDraft.notes}
                          onChange={(event) =>
                            setReviewDraft((current) => ({ ...current, notes: event.target.value }))
                          }
                        />
                      </label>
                      <div className="button-row">
                        <button type="submit">保存复核</button>
                        {reviewStatus && <span className="status-line">{reviewStatus}</span>}
                      </div>
                    </form>
                  </div>
                  {isCodexUsageCase(caseDetail.case) && (
                    <section
                      className="codex-usage-panel"
                      data-testid="codex-usage-panel"
                      aria-label="Codex 使用画像"
                    >
                      <div className="panel-heading compact-heading">
                        <h4>Codex 使用画像</h4>
                        <span>{caseDetail.case.telemetry_source || 'codex-jsonl'}</span>
                      </div>
                      <dl className="codex-usage-grid">
                        <div>
                          <dt>最终状态</dt>
                          <dd>
                            {labelFor(resultStatusLabels, caseDetail.case.status)}
                            {caseDetail.case.codex_error_reason && <small>{caseDetail.case.codex_error_reason}</small>}
                          </dd>
                        </div>
                        <div>
                          <dt>遥测状态</dt>
                          <dd>
                            {labelFor(telemetryLabels, caseDetail.case.telemetry_status || 'unavailable')}
                            {caseDetail.case.telemetry_error && <small>{caseDetail.case.telemetry_error}</small>}
                          </dd>
                        </div>
                        <div>
                          <dt>耗时</dt>
                          <dd>{metricValue(caseDetail.case.agent_duration_seconds?.toFixed(1), 's')}</dd>
                        </div>
                        <div>
                          <dt>Token</dt>
                          <dd>
                            {metricValue(caseDetail.case.total_tokens)}
                            <small>输入 {metricValue(caseDetail.case.prompt_tokens)}</small>
                            <small>缓存 {metricValue(caseDetail.case.cached_input_tokens)}</small>
                            <small>输出 {metricValue(caseDetail.case.completion_tokens)}</small>
                            <small>推理 {metricValue(caseDetail.case.reasoning_tokens)}</small>
                          </dd>
                        </div>
                        <div>
                          <dt>Tool calls</dt>
                          <dd>{metricValue(caseDetail.case.tool_call_count)}</dd>
                        </div>
                        <div>
                          <dt>命令 calls</dt>
                          <dd>{metricValue(caseDetail.case.command_call_count)}</dd>
                        </div>
                        <div>
                          <dt>模型</dt>
                          <dd>{metricValue(caseDetail.case.model_name)}</dd>
                        </div>
                      </dl>
                      <dl className="codex-path-list">
                        <div>
                          <dt>事件 JSONL</dt>
                          <dd>{caseDetail.case.codex_events_path ? <code>{caseDetail.case.codex_events_path}</code> : '-'}</dd>
                        </div>
                        <div>
                          <dt>最终回复</dt>
                          <dd>
                            {caseDetail.case.codex_final_message_path ? (
                              <code>{caseDetail.case.codex_final_message_path}</code>
                            ) : (
                              '-'
                            )}
                          </dd>
                        </div>
                      </dl>
                      <div className="codex-gap-list">
                        <strong>证据缺口</strong>
                        {(caseDetail.case.telemetry_evidence_gaps || []).length > 0 ? (
                          <ul>
                            {(caseDetail.case.telemetry_evidence_gaps || []).map((gap) => (
                              <li key={gap}>{evidenceGapText(gap)}</li>
                            ))}
                          </ul>
                        ) : (
                          <span>未发现结构化缺口</span>
                        )}
                      </div>
                    </section>
                  )}
                  {detailEvidenceNotes.length > 0 && (
                    <section className="evidence-note-panel" aria-label="证据不足解释">
                      <h4>为什么不能高置信判断</h4>
                      <div className="case-evidence-grid">
                        {detailEvidenceNotes.map((note) => (
                          <article key={`${note.title}:${note.message}`}>
                            <strong>{note.title}</strong>
                            <p>{note.message}</p>
                            <small>{note.nextStep}</small>
                          </article>
                        ))}
                      </div>
                    </section>
                  )}
                  {detailHardEvaluation && (
                    <section className="hard-detail-panel" aria-label="硬性检查明细">
                      <div className="panel-heading compact-heading">
                        <h4>硬性检查明细</h4>
                        <span>
                          {detailHardEvaluation.score ?? caseDetail.case.hard_evaluation_score ?? '-'}/
                          {detailHardEvaluation.max_score ?? caseDetail.case.hard_evaluation_max_score ?? '-'}
                        </span>
                      </div>
                      {detailHardEvaluation.error && <p className="status-line">{detailHardEvaluation.error}</p>}
                      {detailHardEvaluation.summary && <p className="status-line">{detailHardEvaluation.summary}</p>}
                      {(detailHardEvaluation.checks || []).length > 0 ? (
                        <ul className="hard-check-list">
                          {(detailHardEvaluation.checks || []).map((check) => (
                            <li className="hard-check-row" key={`${check.name}:${check.status}:${check.message}`}>
                              <strong>{check.name}</strong>
                              <span>{labelFor(evaluationLabels, check.status)}</span>
                              <small>{check.message}</small>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="status-line">没有单项检查明细。</p>
                      )}
                    </section>
                  )}
                  {(caseDetail.soft_evaluation || caseDetail.case.soft_evaluation_payload_path) && (
                    <section className="soft-detail-panel" aria-label="软性复核材料">
                      <h4>软性复核材料</h4>
                      <p>
                        这里展示的是 payload-only 材料位置，context-eval 不会自动调用 OpenAI、Claude 或其他 LLM judge。
                      </p>
                      <dl className="compact-list">
                        <div>
                          <dt>payload</dt>
                          <dd>
                            {caseDetail.soft_evaluation?.payload_path ||
                              caseDetail.case.soft_evaluation_payload_path ||
                              '-'}
                          </dd>
                        </div>
                        <div>
                          <dt>result</dt>
                          <dd>
                            {caseDetail.soft_evaluation?.result_path ||
                              caseDetail.case.soft_evaluation_result_path ||
                              '-'}
                          </dd>
                        </div>
                      </dl>
                    </section>
                  )}
                  <div className="artifact-grid">
                    {caseDetail.patch && (
                      <article className="artifact-pane">
                        <strong>{caseDetail.patch.path}</strong>
                        <pre>{caseDetail.patch.content || caseDetail.patch.error || '空补丁'}</pre>
                      </article>
                    )}
                    {caseDetail.logs.slice(0, 4).map((log) => (
                      <article className="artifact-pane" key={`${log.kind}:${log.path}`}>
                        <strong>
                          {log.kind}: {log.path}
                        </strong>
                        <pre>{log.content || log.error || '空日志'}</pre>
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
