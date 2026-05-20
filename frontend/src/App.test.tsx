import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { App } from './App';
import { reconcileRunScope } from './localConfig';

function jsonResponse(data: unknown, options: { ok?: boolean; status?: number } = {}) {
  const body = JSON.stringify(data);
  return Promise.resolve({
    ok: options.ok ?? true,
    status: options.status ?? 200,
    json: async () => data,
    text: async () => body,
  } as Response);
}

const loadedPayload = {
  ok: true,
  config_path: 'context-eval.yaml',
  tasks_path: 'tasks.yaml',
  config_yaml: 'repo:\n  path: ./fixture-repo\n',
  tasks_yaml: [
    'tasks:',
    '  - id: fix-greeting-punctuation',
    '    prompt: Fix it.',
    '    expected_outcome:',
    '      summary: README contains fixed marker.',
    '    hard_evaluation:',
    '      enabled: true',
    '      required_paths: [README.md]',
    '    soft_evaluation:',
    '      enabled: true',
    '      mode: payload-only',
    '',
  ].join('\n'),
  editable: {
    repo: { path: './fixture-repo', base_ref: 'main' },
    agent: {
      name: 'coco',
      kind: 'coco',
      command: 'coco -y --query-timeout 10m --bash-tool-timeout 5m -p "{prompt}"',
      timeout_minutes: 60,
      network: 'disabled',
    },
    agent_shape: 'agents',
    agents: [
      {
        name: 'coco',
        kind: 'coco',
        command: 'coco -y --query-timeout 10m --bash-tool-timeout 5m -p "{prompt}"',
        timeout_minutes: 60,
        network: 'disabled',
      },
    ],
    tasks_path: './tasks.yaml',
    variants: [
      {
        name: 'baseline',
        description: 'Baseline',
        overlays: [{ source: './contexts/baseline/AGENTS.md', target: 'AGENTS.md' }],
      },
    ],
    tasks: [
      {
        id: 'fix-greeting-punctuation',
        title: 'Fix greeting punctuation',
        prompt: 'Fix it.',
        category: 'runtime',
        difficulty: 'easy',
        validation_commands: ['python -m pytest'],
        expected_outcome: {
          summary: 'README contains fixed marker.',
          acceptance_points: ['The marker is present.'],
        },
        hard_evaluation: {
          enabled: true,
          require_validation_pass: true,
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
      },
    ],
    evaluation_commands: ['python -m pytest'],
    evaluation_timeout_seconds: null,
    output_dir: './runs',
  },
  resolved: {
    repo_path: './fixture-repo',
    output_dir: './runs',
    agents: ['coco'],
    variants: ['baseline'],
    tasks: ['fix-greeting-punctuation'],
  },
};

afterEach(() => {
  window.localStorage.clear();
  vi.unstubAllGlobals();
});

describe('App workflow shell', () => {
  it('renders deterministic fixture fallback when the local server is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('no server')));

    render(<App />);

    expect(screen.getByTestId('local-app-shell')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'context-eval 本地工作台' })).toBeVisible();
    await waitFor(() => expect(screen.getAllByText('示例模式').length).toBeGreaterThan(0));
    expect(screen.getByText('用于比较上下文质量')).toBeVisible();
    expect(screen.getByText(/不是公开 benchmark/)).toBeVisible();
    expect(screen.getAllByRole('heading', { name: '测试用例' }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('heading', { name: '上下文方案' }).length).toBeGreaterThan(0);
    expect(screen.getByText(/AGENTS\.md 工作说明和 skills 技能包/)).toBeVisible();
    expect(screen.getByTestId('matrix-count')).toHaveTextContent('8');
    fireEvent.click(screen.getByText('配置与任务细节'));
    expect(screen.getByRole('heading', { name: '执行器' })).toBeVisible();
    expect(screen.getByRole('heading', { name: '期望结果' })).toBeVisible();
    expect(screen.getByRole('heading', { name: '硬性检查' })).toBeVisible();
    expect(screen.getByRole('heading', { name: '人工反馈规则' })).toBeVisible();
    expect(screen.getByTitle(/会交给 coding agent 的任务描述/)).toBeVisible();
  });

  it('loads Coco hybrid evaluation data from the local server API', async () => {
    const fetchMock = vi.fn((url: string | URL | Request) => {
      const target = String(url);
      if (target === '/api/health') {
        return jsonResponse({ ok: true, initial_config_path: 'context-eval.yaml' });
      }
      if (target === '/api/config/load') {
        return jsonResponse(loadedPayload);
      }
      throw new Error(`unexpected request: ${target}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);

    fireEvent.click(screen.getByText('配置与任务细节'));
    await waitFor(() => expect(screen.getByLabelText('仓库路径')).toHaveValue('./fixture-repo'));
    expect(screen.getByText('Agent 工作说明')).toBeVisible();
    expect(
      screen.getAllByText('coco -y --query-timeout 10m --bash-tool-timeout 5m -p "{prompt}"').length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText('README contains fixed marker.').length).toBeGreaterThan(0);
    expect(screen.getByText('仅生成复核材料')).toBeVisible();

    fireEvent.click(screen.getByRole('button', { name: '加载配置' }));
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/config/load',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('submits raw task YAML unknown fields when saving', async () => {
    const tasksWithUnknown = loadedPayload.tasks_yaml.replace(
      '    prompt: Fix it.',
      '    prompt: Fix it.\n    x_unknown_task_field: keep-me',
    );
    const fetchMock = vi.fn((url: string | URL | Request, init?: RequestInit) => {
      const target = String(url);
      if (target === '/api/health') {
        return jsonResponse({ ok: true, initial_config_path: 'context-eval.yaml' });
      }
      if (target === '/api/config/load') {
        return jsonResponse(loadedPayload);
      }
      if (target === '/api/config/save') {
        return jsonResponse({
          ok: true,
          config_path: 'context-eval.yaml',
          tasks_path: 'tasks.yaml',
          reloaded: {
            ...loadedPayload,
            tasks_yaml: tasksWithUnknown,
          },
        });
      }
      throw new Error(`unexpected request: ${target} ${String(init?.body || '')}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);

    fireEvent.click(screen.getByText('配置与任务细节'));
    await waitFor(() => expect(screen.getByLabelText('tasks.yaml')).toHaveValue(loadedPayload.tasks_yaml));
    fireEvent.change(screen.getByLabelText('tasks.yaml'), {
      target: { value: tasksWithUnknown },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存并重载' }));

    await waitFor(() => {
      expect(screen.getByTestId('save-status')).toHaveTextContent('已保存并从磁盘重载');
    });
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/config/save',
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('x_unknown_task_field: keep-me'),
      }),
    );
    expect(screen.getByLabelText('tasks.yaml')).toHaveValue(tasksWithUnknown);
  });

  it('saves structured task edits and refreshes the run plan', async () => {
    const editedPayload = {
      ...loadedPayload,
      editable: {
        ...loadedPayload.editable,
        tasks: [
          {
            ...loadedPayload.editable.tasks[0],
            prompt: 'Use the visual editor prompt.',
            expected_outcome: {
              ...loadedPayload.editable.tasks[0].expected_outcome,
              summary: 'Visual editor summary.',
            },
          },
        ],
      },
    };
    const fetchMock = vi.fn((url: string | URL | Request, init?: RequestInit) => {
      const target = String(url);
      if (target === '/api/health') {
        return jsonResponse({ ok: true, initial_config_path: 'context-eval.yaml' });
      }
      if (target === '/api/config/load') {
        return jsonResponse(loadedPayload);
      }
      if (target === '/api/config/save-editable') {
        expect(String(init?.body)).toContain('Use the visual editor prompt.');
        expect(String(init?.body)).toContain('Visual editor summary.');
        expect(String(init?.body)).toContain('readme-marker');
        return jsonResponse({
          ok: true,
          config_path: 'context-eval.yaml',
          tasks_path: 'tasks.yaml',
          reloaded: editedPayload,
        });
      }
      if (target === '/api/run-plan') {
        return jsonResponse({
          ok: true,
          case_count: 1,
          cleanup_policy: 'successful',
          jobs: 1,
          trials: 1,
          output_dir: './runs',
          agents: ['coco'],
          tasks: ['fix-greeting-punctuation'],
          variants: ['baseline'],
          cases: [
            {
              case_id: 'fix-greeting-punctuation__baseline__coco',
              agent_name: 'coco',
              agent_kind: 'coco',
              task_id: 'fix-greeting-punctuation',
              variant: 'baseline',
              trial_index: 1,
              repo_ref: 'main',
              command_preview: 'coco -p prompt',
              expected_outcome_summary: 'Visual editor summary.',
              hard_evaluation_enabled: true,
              soft_evaluation_enabled: true,
            },
          ],
        });
      }
      throw new Error(`unexpected request: ${target}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getByLabelText('任务说明')).toHaveValue('Fix it.'));
    expect(screen.getByRole('radiogroup', { name: '任务分类' })).toBeVisible();
    expect(screen.getByRole('radio', { name: '运行时' })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByRole('radiogroup', { name: '难度' })).toBeVisible();
    expect(screen.getByRole('radio', { name: '简单' })).toHaveAttribute('aria-checked', 'true');
    fireEvent.change(screen.getByLabelText('任务说明'), {
      target: { value: 'Use the visual editor prompt.' },
    });
    fireEvent.change(screen.getByLabelText('期望结果摘要'), {
      target: { value: 'Visual editor summary.' },
    });
    fireEvent.click(within(screen.getByRole('group', { name: '硬性检查' })).getByRole('button', { name: '添加' }));
    fireEvent.change(screen.getByLabelText('命令检查名称 1'), {
      target: { value: 'readme-marker' },
    });
    fireEvent.change(screen.getByLabelText('命令检查命令 1'), {
      target: { value: 'python -c "print(\'ok\')"' },
    });
    fireEvent.change(screen.getByLabelText('命令检查期望输出 1'), {
      target: { value: 'ok' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存测试用例' }));

    await waitFor(() => expect(screen.getByTestId('task-save-status')).toHaveTextContent('已保存测试用例并刷新执行计划'));
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/config/save-editable',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/run-plan',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(screen.getAllByText('Visual editor summary.').length).toBeGreaterThan(0);
  });

  it('saves structured variant and agent edits and refreshes the run plan', async () => {
    const editedPayload = {
      ...loadedPayload,
      editable: {
        ...loadedPayload.editable,
        agents: [
          {
            ...loadedPayload.editable.agents[0],
            command: 'coco -y --query-timeout 5m -p "{prompt_file}"',
            timeout_minutes: 15,
            network: 'enabled',
          },
        ],
        agent: {
          ...loadedPayload.editable.agent,
          command: 'coco -y --query-timeout 5m -p "{prompt_file}"',
          timeout_minutes: 15,
          network: 'enabled',
        },
        variants: [
          {
            name: 'baseline',
            description: 'Edited baseline instructions',
            overlays: [{ source: './contexts/edited/AGENTS.md', target: 'AGENTS.md' }],
          },
        ],
      },
    };
    const fetchMock = vi.fn((url: string | URL | Request, init?: RequestInit) => {
      const target = String(url);
      if (target === '/api/health') {
        return jsonResponse({ ok: true, initial_config_path: 'context-eval.yaml' });
      }
      if (target === '/api/config/load') {
        return jsonResponse(loadedPayload);
      }
      if (target === '/api/config/save-editable') {
        const body = JSON.parse(String(init?.body));
        expect(body.editable.variants[0].description).toBe('Edited baseline instructions');
        expect(body.editable.variants[0].overlays[0]).toEqual({
          source: './contexts/edited/AGENTS.md',
          target: 'AGENTS.md',
        });
        expect(body.editable.agents[0].command).toBe('coco -y --query-timeout 5m -p "{prompt_file}"');
        expect(body.editable.agents[0].timeout_minutes).toBe(15);
        expect(body.editable.agents[0].network).toBe('enabled');
        return jsonResponse({
          ok: true,
          config_path: 'context-eval.yaml',
          tasks_path: 'tasks.yaml',
          reloaded: editedPayload,
        });
      }
      if (target === '/api/run-plan') {
        return jsonResponse({
          ok: true,
          case_count: 1,
          cleanup_policy: 'successful',
          jobs: 1,
          trials: 1,
          output_dir: './runs',
          agents: ['coco'],
          tasks: ['fix-greeting-punctuation'],
          variants: ['baseline'],
          cases: [
            {
              case_id: 'fix-greeting-punctuation__baseline__coco',
              agent_name: 'coco',
              agent_kind: 'coco',
              task_id: 'fix-greeting-punctuation',
              variant: 'baseline',
              trial_index: 1,
              repo_ref: 'main',
              command_preview: 'coco -p prompt',
              expected_outcome_summary: 'README contains fixed marker.',
              hard_evaluation_enabled: true,
              soft_evaluation_enabled: true,
            },
          ],
        });
      }
      throw new Error(`unexpected request: ${target}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getByLabelText('方案说明')).toHaveValue('Baseline'));
    fireEvent.change(screen.getByLabelText('方案说明'), {
      target: { value: 'Edited baseline instructions' },
    });
    fireEvent.change(screen.getByLabelText('上下文资料来源路径 1'), {
      target: { value: './contexts/edited/AGENTS.md' },
    });
    fireEvent.change(screen.getByLabelText('执行器命令模板'), {
      target: { value: 'coco -y --query-timeout 5m -p "{prompt_file}"' },
    });
    fireEvent.change(screen.getByLabelText('执行器超时分钟'), {
      target: { value: '15' },
    });
    fireEvent.change(screen.getByLabelText('执行器联网权限'), {
      target: { value: 'enabled' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存上下文方案' }));

    await waitFor(() => {
      expect(screen.getByTestId('variant-save-status')).toHaveTextContent('已保存配置并刷新执行计划');
    });
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/config/save-editable',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/run-plan',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(screen.getByLabelText('方案说明')).toHaveValue('Edited baseline instructions');
  });

  it('blocks invalid task fields before submitting structured saves', async () => {
    const fetchMock = vi.fn((url: string | URL | Request) => {
      const target = String(url);
      if (target === '/api/health') {
        return jsonResponse({ ok: true, initial_config_path: 'context-eval.yaml' });
      }
      if (target === '/api/config/load') {
        return jsonResponse(loadedPayload);
      }
      throw new Error(`unexpected request: ${target}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getByLabelText('任务说明')).toHaveValue('Fix it.'));
    fireEvent.change(screen.getByLabelText('任务说明'), { target: { value: ' ' } });
    fireEvent.change(screen.getByLabelText('命令 1'), { target: { value: ' ' } });
    fireEvent.click(screen.getByRole('button', { name: '保存测试用例' }));

    expect(await screen.findByText('fix-greeting-punctuation: 任务说明不能为空')).toBeVisible();
    expect(screen.getByText('fix-greeting-punctuation: 第 1 条验证命令不能为空')).toBeVisible();
    expect(fetchMock).not.toHaveBeenCalledWith(
      '/api/config/save-editable',
      expect.anything(),
    );
  });

  it('blocks invalid variant and agent fields before structured saves', async () => {
    const fetchMock = vi.fn((url: string | URL | Request) => {
      const target = String(url);
      if (target === '/api/health') {
        return jsonResponse({ ok: true, initial_config_path: 'context-eval.yaml' });
      }
      if (target === '/api/config/load') {
        return jsonResponse(loadedPayload);
      }
      throw new Error(`unexpected request: ${target}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getByLabelText('方案名称')).toHaveValue('baseline'));
    fireEvent.change(screen.getByLabelText('方案名称'), { target: { value: ' ' } });
    fireEvent.change(screen.getByLabelText('上下文资料来源路径 1'), { target: { value: ' ' } });
    fireEvent.change(screen.getByLabelText('执行器命令模板'), { target: { value: ' ' } });
    fireEvent.change(screen.getByLabelText('执行器超时分钟'), { target: { value: '0' } });
    await waitFor(() => expect(screen.getByLabelText('方案名称')).toHaveValue(' '));
    await waitFor(() => expect(screen.getByLabelText('执行器超时分钟')).toHaveValue(0));
    fireEvent.click(screen.getByRole('button', { name: '保存执行器配置' }));

    expect(await screen.findByText('第 1 个上下文方案名称不能为空')).toBeVisible();
    expect(screen.getByText('第 1 个上下文方案的第 1 个上下文资料来源路径不能为空')).toBeVisible();
    expect(screen.getByText('第 1 个执行器命令模板不能为空')).toBeVisible();
    expect(screen.getByText('第 1 个执行器超时必须大于 0')).toBeVisible();
    expect(fetchMock).not.toHaveBeenCalledWith(
      '/api/config/save-editable',
      expect.anything(),
    );
  });

  it('passes selected task, variant, and agent scope into plan and run requests', async () => {
    const scopedPayload = {
      ...loadedPayload,
      editable: {
        ...loadedPayload.editable,
        agents: [
          loadedPayload.editable.agents[0],
          {
            name: 'codex',
            kind: 'codex-cli',
            command: 'codex exec "{prompt_file}"',
            timeout_minutes: 30,
            network: 'disabled',
          },
        ],
        tasks: [
          loadedPayload.editable.tasks[0],
          {
            ...loadedPayload.editable.tasks[0],
            id: 'second-task',
            title: 'Second task',
            prompt: 'Second prompt.',
          },
        ],
        variants: [
          loadedPayload.editable.variants[0],
          { name: 'experiment', description: 'Experiment', overlays: [] },
        ],
      },
      resolved: {
        ...loadedPayload.resolved,
        agents: ['coco', 'codex'],
        tasks: ['fix-greeting-punctuation', 'second-task'],
        variants: ['baseline', 'experiment'],
      },
    };
    const fetchMock = vi.fn((url: string | URL | Request, init?: RequestInit) => {
      const target = String(url);
      if (target === '/api/health') {
        return jsonResponse({ ok: true, initial_config_path: 'context-eval.yaml' });
      }
      if (target === '/api/config/load') {
        return jsonResponse(scopedPayload);
      }
      if (target === '/api/preflight') {
        return jsonResponse({ ok: true, checks: ['schema', 'repo'] });
      }
      if (target === '/api/run-plan') {
        const body = JSON.parse(String(init?.body));
        expect(body.task_ids).toEqual(['second-task']);
        expect(body.variants).toEqual(['experiment']);
        expect(body.agents).toEqual(['codex']);
        return jsonResponse({
          ok: true,
          case_count: 1,
          cleanup_policy: 'successful',
          jobs: 1,
          trials: 1,
          output_dir: './runs',
          agents: ['codex'],
          tasks: ['second-task'],
          variants: ['experiment'],
          cases: [
            {
              case_id: 'second-task__experiment__codex',
              agent_name: 'codex',
              agent_kind: 'codex-cli',
              task_id: 'second-task',
              variant: 'experiment',
              trial_index: 1,
              repo_ref: 'main',
              command_preview: 'codex exec prompt',
              expected_outcome_summary: 'README contains fixed marker.',
              hard_evaluation_enabled: true,
              soft_evaluation_enabled: true,
            },
          ],
        });
      }
      if (target === '/api/runs') {
        const body = JSON.parse(String(init?.body));
        expect(body.task_ids).toEqual(['second-task']);
        expect(body.variants).toEqual(['experiment']);
        expect(body.agents).toEqual(['codex']);
        return jsonResponse({
          ok: true,
          app_run_id: 'run-scope',
          status: 'completed',
          run_dir: './runs/run-scope',
          case_count: 1,
          completed_cases: 1,
        });
      }
      if (target === '/api/runs/run-scope/logs') {
        return jsonResponse({ ok: true, console: ['done'], files: [] });
      }
      if (target.startsWith('/api/results')) {
        return jsonResponse({
          ok: true,
          overview: {
            case_count: 1,
            failed_count: 0,
            timeout_count: 0,
            low_confidence_count: 0,
            telemetry_gap_count: 0,
          },
          cases: [
            {
              case_id: 'second-task__experiment__codex',
              agent_name: 'codex',
              task_id: 'second-task',
              variant: 'experiment',
              status: 'completed',
              validation_status: 'passed',
              confidence: 'high',
              hard_evaluation_status: 'passed',
              hard_evaluation_score: 1,
              hard_evaluation_max_score: 1,
              soft_evaluation_status: 'payload_generated',
            },
          ],
        });
      }
      throw new Error(`unexpected request: ${target}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getByLabelText('任务 second-task')).toBeChecked());
    fireEvent.click(screen.getByLabelText('任务 fix-greeting-punctuation'));
    fireEvent.click(screen.getByLabelText('上下文方案 baseline'));
    fireEvent.click(screen.getByLabelText('执行器 coco'));
    fireEvent.click(screen.getByRole('button', { name: '刷新执行计划' }));

    await waitFor(() => expect(screen.getByTestId('planned-case-count')).toHaveTextContent('1'));
    expect(screen.getByText('second-task__experiment__codex')).toBeVisible();

    fireEvent.click(screen.getByRole('button', { name: '开始运行' }));
    await waitFor(() => expect(screen.getByTestId('run-status')).toHaveTextContent('已完成 1/1'));
    expect(screen.getAllByText('codex').length).toBeGreaterThan(0);
  });

  it('shows API errors from structured saves', async () => {
    const fetchMock = vi.fn((url: string | URL | Request) => {
      const target = String(url);
      if (target === '/api/health') {
        return jsonResponse({ ok: true, initial_config_path: 'context-eval.yaml' });
      }
      if (target === '/api/config/load') {
        return jsonResponse(loadedPayload);
      }
      if (target === '/api/config/save-editable') {
        return jsonResponse(
          { ok: false, error: 'tasks.0.prompt: server validation failed' },
          { ok: false, status: 400 },
        );
      }
      throw new Error(`unexpected request: ${target}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getByLabelText('任务说明')).toHaveValue('Fix it.'));
    fireEvent.click(screen.getByRole('button', { name: '保存测试用例' }));

    await waitFor(() => {
      expect(screen.getByText('错误: tasks.0.prompt: server validation failed')).toBeVisible();
    });
  });

  it('shows hard and soft result status after a completed run', async () => {
    const fetchMock = vi.fn((url: string | URL | Request) => {
      const target = String(url);
      if (target === '/api/health') {
        return jsonResponse({ ok: true, initial_config_path: 'context-eval.yaml' });
      }
      if (target === '/api/config/load') {
        return jsonResponse(loadedPayload);
      }
      if (target === '/api/preflight') {
        return jsonResponse({
          ok: true,
          checks: ['config_structure', 'repo_path', 'git_ref'],
        });
      }
      if (target === '/api/run-plan') {
        return jsonResponse({
          ok: true,
          case_count: 1,
          cleanup_policy: 'successful',
          jobs: 1,
          trials: 1,
          output_dir: './runs',
          agents: ['coco'],
          tasks: ['fix-greeting-punctuation'],
          variants: ['baseline'],
          cases: [
            {
              case_id: 'fix-greeting-punctuation__baseline__coco',
              agent_name: 'coco',
              agent_kind: 'coco',
              task_id: 'fix-greeting-punctuation',
              variant: 'baseline',
              trial_index: 1,
              repo_ref: 'main',
              command_preview: 'coco -y --query-timeout 10m --bash-tool-timeout 5m -p "Fix it."',
              expected_outcome_summary: 'README contains fixed marker.',
              hard_evaluation_enabled: true,
              soft_evaluation_enabled: true,
            },
          ],
        });
      }
      if (target === '/api/runs') {
        return jsonResponse({
          ok: true,
          app_run_id: 'run-a',
          status: 'completed',
          run_dir: './runs/run-a',
          case_count: 1,
          completed_cases: 1,
        });
      }
      if (target === '/api/runs/run-a/logs') {
        return jsonResponse({ ok: true, console: ['done'], files: [] });
      }
      if (target === '/api/runs/run-a') {
        return jsonResponse({
          ok: true,
          app_run_id: 'run-a',
          status: 'completed',
          run_dir: './runs/run-a',
          case_count: 1,
          completed_cases: 1,
        });
      }
      if (target.startsWith('/api/results')) {
        const requestedBaseline = new URL(target, 'http://local.test').searchParams.get('baseline_variant');
        const selectedBaseline = requestedBaseline || 'baseline';
        return jsonResponse({
          ok: true,
          overview: {
            case_count: 1,
            failed_count: 0,
            timeout_count: 0,
            low_confidence_count: 0,
            telemetry_gap_count: 0,
          },
          selected_baseline_variant: selectedBaseline,
          available_baseline_variants: ['baseline', 'experiment'],
          baseline_selection_notice: requestedBaseline === 'removed' ? '已清理不存在的比较基线 removed，改用 baseline。' : null,
          evaluation_explanation: {
            local_only: '仅比较本地 artifact 中的观察结果，不是公开 benchmark、绝对排名或 agent leaderboard。',
            validation_confidence: {
              high: '有 validation commands 且全部通过。',
              medium: '有 validation commands 但失败或超时。',
              low: '没有 validation commands，不能高置信判断。',
            },
            hard_evaluation: {
              score_meaning: 'hard score 是通过检查数 / 可评分检查数，不是综合质量分。',
              skipped_meaning: 'skipped 表示本地产物不足。',
            },
            soft_evaluation: {
              mode: 'payload-only',
              meaning: 'soft evaluation 只生成 payload-only 复核材料，不自动调用 LLM judge。',
            },
            manual_review: {
              meaning: 'manual review 是人工复核证据和结论，不是自动评分。',
            },
            evidence_limits: ['无 validation、hard skipped 或 telemetry missing 时只能提示证据不足。'],
          },
          compare_groups: [
            {
              group_id: 'fix-greeting-punctuation__coco__trial-1',
              task_id: 'fix-greeting-punctuation',
              agent_name: 'coco',
              trial_index: 1,
              baseline_variant: selectedBaseline,
              comparison_variant: selectedBaseline === 'baseline' ? 'experiment' : 'baseline',
              experiment_variant: 'experiment',
              baseline_case_id: 'fix-greeting-punctuation__baseline__coco',
              comparison_case_id: 'fix-greeting-punctuation__experiment__coco',
              experiment_case_id: 'fix-greeting-punctuation__experiment__coco',
              verdict: 'comparison_improved',
              hard_delta: 1,
              hard_check_delta: 1,
              validation_delta: 0,
              total_tokens_delta: -20,
              summary: '对比对象 hard evaluation 增加 1，validation 结果未变化。',
              evidence_gaps: [],
            },
          ],
          cases: [
            {
              case_id: 'fix-greeting-punctuation__baseline__coco',
              agent_name: 'coco',
              task_id: 'fix-greeting-punctuation',
              variant: 'baseline',
              status: 'completed',
              validation_status: 'passed',
              confidence: 'high',
              telemetry_status: 'collected',
              telemetry_source: 'codex-jsonl',
              agent_duration_seconds: 0.1,
              prompt_tokens: 20,
              cached_input_tokens: 5,
              completion_tokens: 7,
              total_tokens: 27,
              reasoning_tokens: 3,
              reasoning_step_count: 2,
              tool_call_count: 1,
              command_call_count: 1,
              model_name: 'gpt-5.4',
              telemetry_evidence_gaps: [],
              codex_events_path: 'artifacts/fix-greeting-punctuation__baseline__coco/codex-events.jsonl',
              codex_final_message_path: 'artifacts/fix-greeting-punctuation__baseline__coco/codex-final-message.md',
              changed_files: 1,
              hard_evaluation_status: 'passed',
              hard_evaluation_score: 4,
              hard_evaluation_max_score: 4,
              hard_evaluation_passed_checks: 4,
              hard_evaluation_failed_checks: 0,
              soft_evaluation_status: 'payload_generated',
              soft_evaluation_payload_path:
                'artifacts/fix-greeting-punctuation__baseline__coco/soft_evaluation_payload.json',
              patch_path: 'patches/fix-greeting-punctuation__baseline__coco.patch',
              stdout_path: 'logs/fix-greeting-punctuation__baseline__coco.agent.stdout.log',
              stderr_path: 'logs/fix-greeting-punctuation__baseline__coco.agent.stderr.log',
              manual_review: {
                case_id: 'fix-greeting-punctuation__baseline__coco',
                decision: 'not_reviewed',
                confidence: 'unknown',
                reviewer: '',
                notes: '',
                updated_at: null,
              },
            },
          ],
        });
      }
      if (target.startsWith('/api/case-detail')) {
        return jsonResponse({
          ok: true,
          case: {
            case_id: 'fix-greeting-punctuation__baseline__coco',
            task_id: 'fix-greeting-punctuation',
            variant: 'baseline',
            agent_name: 'coco',
            status: 'completed',
            validation_status: 'passed',
            confidence: 'high',
            telemetry_status: 'collected',
            telemetry_source: 'codex-jsonl',
            agent_duration_seconds: 0.1,
            prompt_tokens: 20,
            cached_input_tokens: 5,
            completion_tokens: 7,
            total_tokens: 27,
            reasoning_tokens: 3,
            reasoning_step_count: 2,
            tool_call_count: 1,
            command_call_count: 1,
            model_name: 'gpt-5.4',
            telemetry_evidence_gaps: [],
            codex_events_path: 'artifacts/fix-greeting-punctuation__baseline__coco/codex-events.jsonl',
            codex_final_message_path: 'artifacts/fix-greeting-punctuation__baseline__coco/codex-final-message.md',
            hard_evaluation_status: 'passed',
            hard_evaluation_score: 4,
            hard_evaluation_max_score: 4,
            soft_evaluation_status: 'payload_generated',
            soft_evaluation_payload_path:
              'artifacts/fix-greeting-punctuation__baseline__coco/soft_evaluation_payload.json',
            manual_review: {
              case_id: 'fix-greeting-punctuation__baseline__coco',
              decision: 'not_reviewed',
              confidence: 'unknown',
              reviewer: '',
              notes: '',
              updated_at: null,
            },
          },
          patch: {
            path: 'patches/fix-greeting-punctuation__baseline__coco.patch',
            content: 'diff --git a/README.md b/README.md\n+context-eval marker\n',
            exists: true,
          },
          logs: [{ kind: 'agent_stdout', path: 'logs/stdout.log', content: 'done', exists: true }],
          hard_evaluation: {
            status: 'passed',
            score: 4,
            max_score: 4,
            checks: [{ name: 'README.md', status: 'passed', message: 'found expected marker' }],
          },
          soft_evaluation: {
            status: 'payload_generated',
            payload_path: 'artifacts/fix-greeting-punctuation__baseline__coco/soft_evaluation_payload.json',
            result_path: null,
          },
          manual_review: {
            case_id: 'fix-greeting-punctuation__baseline__coco',
            decision: 'not_reviewed',
            confidence: 'unknown',
            reviewer: '',
            notes: '',
            updated_at: null,
          },
        });
      }
      if (target === '/api/manual-review') {
        return jsonResponse({
          ok: true,
          case_id: 'fix-greeting-punctuation__baseline__coco',
          review: {
            case_id: 'fix-greeting-punctuation__baseline__coco',
            decision: 'pass',
            confidence: 'high',
            reviewer: 'manual',
            notes: 'Looks good.',
            updated_at: '2026-05-19T16:30:00',
          },
        });
      }
      throw new Error(`unexpected request: ${target}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getAllByText('Fix greeting punctuation').length).toBeGreaterThan(0));
    fireEvent.click(screen.getByRole('button', { name: '开始运行' }));
    await waitFor(() => expect(screen.getByTestId('preflight-status')).toHaveTextContent('运行前检查通过'));
    await waitFor(() => expect(screen.getByTestId('planned-case-count')).toHaveTextContent('1'));
    expect(screen.queryByRole('button', { name: '运行预检' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '生成矩阵' })).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('通过 4/4')).toBeVisible());
    expect(screen.getByText('结果已生成')).toBeVisible();
    expect(screen.getByRole('button', { name: '查看结果' })).toBeVisible();
    expect(screen.getByText('已生成待复核材料')).toBeVisible();
    expect(screen.getByText('27')).toBeVisible();
    expect(screen.getByText('轮次 2')).toBeVisible();
    expect(screen.getByText('评分依据和边界')).toBeVisible();
    expect(screen.getByText('soft evaluation 只生成 payload-only 复核材料，不自动调用 LLM judge。')).toBeVisible();
    expect(screen.getByLabelText('比较基线')).toHaveValue('baseline');
    expect(screen.getByText('对比对象改善')).toBeVisible();
    expect(screen.getByText('对比对象 hard evaluation 增加 1，validation 结果未变化。')).toBeVisible();
    fireEvent.change(screen.getByLabelText('比较基线'), { target: { value: 'experiment' } });
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/results?run_dir=.%2Fruns%2Frun-a&baseline_variant=experiment',
        expect.any(Object),
      ),
    );

    fireEvent.click(screen.getByRole('button', { name: '查看详情' }));
    await waitFor(() => expect(screen.getByRole('heading', { name: '用例详情' })).toBeVisible());
    expect(screen.getByText('patches/fix-greeting-punctuation__baseline__coco.patch')).toBeVisible();
    expect(screen.getByText(/context-eval marker/)).toBeVisible();
    expect(screen.getByRole('heading', { name: '硬性检查明细' })).toBeVisible();
    expect(screen.getByText('found expected marker')).toBeVisible();
    expect(screen.getByTestId('codex-usage-panel')).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Codex 使用画像' })).toBeVisible();
    expect(screen.getByText('输入 20')).toBeVisible();
    expect(screen.getByText('缓存 5')).toBeVisible();
    expect(screen.getByText('输出 7')).toBeVisible();
    expect(screen.getAllByText('推理 3').length).toBeGreaterThan(0);
    expect(screen.getByText('命令 calls')).toBeVisible();
    expect(screen.getAllByText('gpt-5.4').length).toBeGreaterThan(0);
    expect(screen.getByText('未发现结构化缺口')).toBeVisible();
    expect(screen.getByText('artifacts/fix-greeting-punctuation__baseline__coco/codex-events.jsonl')).toBeVisible();
    expect(screen.getByText('artifacts/fix-greeting-punctuation__baseline__coco/codex-final-message.md')).toBeVisible();

    fireEvent.change(screen.getByLabelText('反馈结论'), { target: { value: 'pass' } });
    fireEvent.change(screen.getByLabelText('反馈可信度'), { target: { value: 'high' } });
    fireEvent.change(screen.getByLabelText('反馈人'), { target: { value: 'manual' } });
    fireEvent.change(screen.getByLabelText('反馈备注'), { target: { value: 'Looks good.' } });
    fireEvent.click(screen.getByRole('button', { name: '保存人工反馈' }));
    await waitFor(() => expect(screen.getByText('人工反馈已保存')).toBeVisible());
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/manual-review',
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('"decision":"pass"'),
      }),
    );
  });
});

describe('run scope reconciliation', () => {
  it('reports a cleanup notice when an all-selected scope loses deleted values', () => {
    const reconciled = reconcileRunScope(
      {
        task_ids: ['task-a', 'task-b'],
        variants: ['baseline', 'experiment'],
        agents: ['coco', 'codex'],
      },
      {
        task_ids: ['task-a', 'task-b'],
        variants: ['baseline', 'experiment'],
        agents: ['coco', 'codex'],
      },
      {
        task_ids: ['task-a'],
        variants: ['baseline'],
        agents: ['coco'],
      },
      true,
    );

    expect(reconciled.scope).toEqual({
      task_ids: ['task-a'],
      variants: ['baseline'],
      agents: ['coco'],
    });
    expect(reconciled.changed).toBe(true);
  });
});
