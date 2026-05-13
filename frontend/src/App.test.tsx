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
  tasks_yaml: 'tasks:\n  - id: fix-greeting-punctuation\n    prompt: Fix it.\n',
  editable: {
    repo: { path: './fixture-repo', base_ref: 'main' },
    agent: {
      name: 'browser-fake-agent',
      kind: 'custom',
      command: 'python scripts/example_agent.py "{prompt_file}"',
      timeout_minutes: 1,
      network: 'disabled',
    },
    agent_shape: 'agent',
    agents: [],
    tasks_path: './tasks.yaml',
    variants: [{ name: 'baseline', description: 'Baseline', overlays: [] }],
    tasks: [
      {
        id: 'fix-greeting-punctuation',
        title: 'Fix greeting punctuation',
        prompt: 'Fix it.',
        validation_commands: ['python -m pytest'],
      },
    ],
    evaluation_commands: ['python -m pytest'],
    evaluation_timeout_seconds: null,
    output_dir: './runs',
  },
  resolved: {
    repo_path: './fixture-repo',
    output_dir: './runs',
    agents: ['browser-fake-agent'],
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
    expect(screen.getByText('仅使用本地产物')).toBeVisible();
    await waitFor(() => expect(screen.getAllByText('示例模式').length).toBeGreaterThan(0));
    expect(screen.getByTestId('matrix-count')).toHaveTextContent('8');
    expect(screen.getByText('codex-cli')).toBeVisible();
    expect(screen.getByText('traecli')).toBeVisible();
  });

  it('loads config data from the local server API', async () => {
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
    expect(screen.getByText('browser-fake-agent')).toBeVisible();
    expect(screen.getByText('fix-greeting-punctuation')).toBeVisible();
    expect(screen.getByText('python -m pytest')).toBeVisible();

    fireEvent.click(screen.getByRole('button', { name: '加载配置' }));
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/config/load',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('saves config and task YAML, then reloads parsed disk state', async () => {
    const reloadedPayload = {
      ...loadedPayload,
      tasks_yaml: loadedPayload.tasks_yaml.replace('Fix it.', '保存后的提示。'),
      editable: {
        ...loadedPayload.editable,
        tasks: [
          {
            ...loadedPayload.editable.tasks[0],
            title: '保存后的标题',
            prompt: '保存后的提示。',
            category: 'docs',
            difficulty: 'medium',
          },
        ],
      },
    };
    const fetchMock = vi.fn((url: string | URL | Request) => {
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
          reloaded: reloadedPayload,
        });
      }
      throw new Error(`unexpected request: ${target}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getByLabelText('tasks.yaml')).toHaveValue(loadedPayload.tasks_yaml));
    fireEvent.change(screen.getByLabelText('tasks.yaml'), {
      target: {
        value: loadedPayload.tasks_yaml
          .replace('Fix it.', '保存后的提示。')
          .replace('fix-greeting-punctuation', 'fix-greeting-copy'),
      },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存并重载' }));

    await waitFor(() => {
      expect(screen.getByTestId('save-status')).toHaveTextContent('已保存并从磁盘重载');
    });
    expect(screen.getByText('保存后的标题')).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/config/save',
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('保存后的提示。'),
      }),
    );
  });
});
