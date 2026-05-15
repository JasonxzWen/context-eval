import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { App } from './App';

function jsonResponse(data: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
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
    variants: [{ name: 'baseline', description: 'Baseline', overlays: [] }],
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
    expect(screen.getByRole('heading', { name: 'Coco Agent' })).toBeVisible();
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

    await waitFor(() => expect(screen.getByLabelText('仓库路径')).toHaveValue('./fixture-repo'));
    expect(
      screen.getByText('coco -y --query-timeout 10m --bash-tool-timeout 5m -p "{prompt}"'),
    ).toBeVisible();
    expect(screen.getByText('README contains fixed marker.')).toBeVisible();
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

  it('shows hard and soft result status after a completed run', async () => {
    const fetchMock = vi.fn((url: string | URL | Request) => {
      const target = String(url);
      if (target === '/api/health') {
        return jsonResponse({ ok: true, initial_config_path: 'context-eval.yaml' });
      }
      if (target === '/api/config/load') {
        return jsonResponse(loadedPayload);
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
          cases: [
            {
              case_id: 'fix-greeting-punctuation__baseline__coco',
              agent_name: 'coco',
              task_id: 'fix-greeting-punctuation',
              variant: 'baseline',
              status: 'completed',
              validation_status: 'passed',
              confidence: 'high',
              changed_files: 1,
              hard_evaluation_status: 'passed',
              hard_evaluation_score: 4,
              hard_evaluation_max_score: 4,
              soft_evaluation_status: 'payload_generated',
              soft_evaluation_payload_path:
                'artifacts/fix-greeting-punctuation__baseline__coco/soft_evaluation_payload.json',
            },
          ],
        });
      }
      throw new Error(`unexpected request: ${target}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getByLabelText('仓库路径')).toHaveValue('./fixture-repo'));
    fireEvent.click(screen.getByRole('button', { name: '生成计划' }));
    await waitFor(() => expect(screen.getByTestId('planned-case-count')).toHaveTextContent('1'));
    fireEvent.click(screen.getByRole('button', { name: '开始运行' }));
    await waitFor(() => expect(screen.getByText('hard passed 4/4')).toBeVisible());
    expect(screen.getByText('soft payload_generated')).toBeVisible();
  });
});
