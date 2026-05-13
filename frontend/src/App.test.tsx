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
    expect(screen.getByRole('heading', { name: 'Context Eval Local App' })).toBeVisible();
    expect(screen.getByText('Local artifacts only')).toBeVisible();
    expect(screen.getByText('Validation shell')).toBeVisible();
    await waitFor(() => expect(screen.getByText('fixture')).toBeVisible());
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

    await waitFor(() => expect(screen.getByLabelText('Repo path')).toHaveValue('./fixture-repo'));
    expect(screen.getByText('browser-fake-agent')).toBeVisible();
    expect(screen.getByText('fix-greeting-punctuation')).toBeVisible();
    expect(screen.getByText('python -m pytest')).toBeVisible();

    fireEvent.click(screen.getByRole('button', { name: 'Load config' }));
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/config/load',
      expect.objectContaining({ method: 'POST' }),
    );
  });
});
