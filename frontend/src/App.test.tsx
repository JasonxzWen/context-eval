import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { App } from './App';
import { reconcileRunScope } from './localConfig';

function jsonResponse(data: unknown, options: { ok?: boolean; status?: number } = {}) {
  return Promise.resolve({
    ok: options.ok ?? true,
    status: options.status ?? 200,
    json: async () => data,
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
  vi.unstubAllGlobals();
});

describe('App workflow shell', () => {
  it('renders deterministic fixture fallback when the local server is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('no server')));

    render(<App />);

    expect(screen.getByTestId('local-app-shell')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'context-eval 本地工作台' })).toBeVisible();
    await waitFor(() => expect(screen.getAllByText('示例模式').length).toBeGreaterThan(0));
    expect(screen.getByTestId('matrix-count')).toHaveTextContent('8');
    fireEvent.click(screen.getByText('配置与任务细节'));
    expect(screen.getByRole('heading', { name: 'Agent' })).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Expected Outcome' })).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Hard Evaluation' })).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Soft Evaluation' })).toBeVisible();
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
    expect(
      screen.getAllByText('coco -y --query-timeout 10m --bash-tool-timeout 5m -p "{prompt}"').length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText('README contains fixed marker.').length).toBeGreaterThan(0);
    expect(screen.getByText('payload-only')).toBeVisible();

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

    await waitFor(() => expect(screen.getByLabelText('Prompt')).toHaveValue('Fix it.'));
    fireEvent.change(screen.getByLabelText('Prompt'), {
      target: { value: 'Use the visual editor prompt.' },
    });
    fireEvent.change(screen.getByLabelText('Expected outcome summary'), {
      target: { value: 'Visual editor summary.' },
    });
    fireEvent.click(within(screen.getByRole('group', { name: 'Hard checks' })).getByRole('button', { name: '添加' }));
    fireEvent.change(screen.getByLabelText('hard check label 1'), {
      target: { value: 'readme-marker' },
    });
    fireEvent.change(screen.getByLabelText('hard check command 1'), {
      target: { value: 'python -c "print(\'ok\')"' },
    });
    fireEvent.change(screen.getByLabelText('hard check expected 1'), {
      target: { value: 'ok' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存任务' }));

    await waitFor(() => expect(screen.getByTestId('task-save-status')).toHaveTextContent('已保存任务并刷新 run plan'));
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

    await waitFor(() => expect(screen.getByLabelText('variant description')).toHaveValue('Baseline'));
    fireEvent.change(screen.getByLabelText('variant description'), {
      target: { value: 'Edited baseline instructions' },
    });
    fireEvent.change(screen.getByLabelText('overlay source 1'), {
      target: { value: './contexts/edited/AGENTS.md' },
    });
    fireEvent.change(screen.getByLabelText('agent command'), {
      target: { value: 'coco -y --query-timeout 5m -p "{prompt_file}"' },
    });
    fireEvent.change(screen.getByLabelText('agent timeout minutes'), {
      target: { value: '15' },
    });
    fireEvent.change(screen.getByLabelText('agent network'), {
      target: { value: 'enabled' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存 variant 配置' }));

    await waitFor(() => {
      expect(screen.getByTestId('variant-save-status')).toHaveTextContent('已保存配置并刷新 run plan');
    });
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/config/save-editable',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/run-plan',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(screen.getByLabelText('variant description')).toHaveValue('Edited baseline instructions');
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

    await waitFor(() => expect(screen.getByLabelText('Prompt')).toHaveValue('Fix it.'));
    fireEvent.change(screen.getByLabelText('Prompt'), { target: { value: ' ' } });
    fireEvent.change(screen.getByLabelText('命令 1'), { target: { value: ' ' } });
    fireEvent.click(screen.getByRole('button', { name: '保存任务' }));

    expect(await screen.findByText('fix-greeting-punctuation: prompt 不能为空')).toBeVisible();
    expect(screen.getByText('fix-greeting-punctuation: validation command 1 不能为空')).toBeVisible();
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

    await waitFor(() => expect(screen.getByLabelText('variant name')).toHaveValue('baseline'));
    fireEvent.change(screen.getByLabelText('variant name'), { target: { value: ' ' } });
    fireEvent.change(screen.getByLabelText('overlay source 1'), { target: { value: ' ' } });
    fireEvent.change(screen.getByLabelText('agent command'), { target: { value: ' ' } });
    fireEvent.change(screen.getByLabelText('agent timeout minutes'), { target: { value: '0' } });
    await waitFor(() => expect(screen.getByLabelText('variant name')).toHaveValue(' '));
    await waitFor(() => expect(screen.getByLabelText('agent timeout minutes')).toHaveValue(0));
    fireEvent.click(screen.getByRole('button', { name: '保存 agent 配置' }));

    expect(await screen.findByText('variant 1 name 不能为空')).toBeVisible();
    expect(screen.getByText('variant 1 overlay 1 source 不能为空')).toBeVisible();
    expect(screen.getByText('agent profile 1 command 不能为空')).toBeVisible();
    expect(screen.getByText('agent profile 1 timeout 必须大于 0')).toBeVisible();
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

    await waitFor(() => expect(screen.getByLabelText('task second-task')).toBeChecked());
    fireEvent.click(screen.getByLabelText('task fix-greeting-punctuation'));
    fireEvent.click(screen.getByLabelText('variant baseline'));
    fireEvent.click(screen.getByLabelText('agent coco'));
    fireEvent.click(screen.getByRole('button', { name: '刷新 run plan' }));

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

    await waitFor(() => expect(screen.getByLabelText('Prompt')).toHaveValue('Fix it.'));
    fireEvent.click(screen.getByRole('button', { name: '保存任务' }));

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
        return jsonResponse({
          ok: true,
          overview: {
            case_count: 1,
            failed_count: 0,
            timeout_count: 0,
            low_confidence_count: 0,
            telemetry_gap_count: 0,
          },
          compare_groups: [
            {
              group_id: 'fix-greeting-punctuation__coco__trial-1',
              task_id: 'fix-greeting-punctuation',
              agent_name: 'coco',
              trial_index: 1,
              baseline_variant: 'baseline',
              experiment_variant: 'experiment',
              baseline_case_id: 'fix-greeting-punctuation__baseline__coco',
              experiment_case_id: 'fix-greeting-punctuation__experiment__coco',
              verdict: 'experiment_improved',
              hard_delta: 1,
              validation_delta: 0,
              total_tokens_delta: -20,
              summary: 'experiment improved hard evaluation without changing validation status',
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
              total_tokens: 180,
              reasoning_tokens: 24,
              reasoning_step_count: 2,
              tool_call_count: 3,
              changed_files: 1,
              hard_evaluation_status: 'passed',
              hard_evaluation_score: 4,
              hard_evaluation_max_score: 4,
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
            hard_evaluation_status: 'passed',
            hard_evaluation_score: 4,
            hard_evaluation_max_score: 4,
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
          hard_evaluation: { status: 'passed', checks: [] },
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
    await waitFor(() => expect(screen.getByText('hard passed 4/4')).toBeVisible());
    expect(screen.getByText('结果已生成')).toBeVisible();
    expect(screen.getByRole('button', { name: '查看 Results' })).toBeVisible();
    expect(screen.getByText('soft payload_generated')).toBeVisible();
    expect(screen.getByText('180')).toBeVisible();
    expect(screen.getByText('rounds 2')).toBeVisible();
    expect(screen.getByText('experiment_improved')).toBeVisible();
    expect(screen.getByText('experiment improved hard evaluation without changing validation status')).toBeVisible();

    fireEvent.click(screen.getByRole('button', { name: '查看详情' }));
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Case Detail' })).toBeVisible());
    expect(screen.getByText('patches/fix-greeting-punctuation__baseline__coco.patch')).toBeVisible();
    expect(screen.getByText(/context-eval marker/)).toBeVisible();

    fireEvent.change(screen.getByLabelText('review decision'), { target: { value: 'pass' } });
    fireEvent.change(screen.getByLabelText('review confidence'), { target: { value: 'high' } });
    fireEvent.change(screen.getByLabelText('reviewer'), { target: { value: 'manual' } });
    fireEvent.change(screen.getByLabelText('review notes'), { target: { value: 'Looks good.' } });
    fireEvent.click(screen.getByRole('button', { name: '保存 Review' }));
    await waitFor(() => expect(screen.getByText('Review 已保存')).toBeVisible());
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
