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
    '    case_type: bugfix',
    '    repo_ref: main',
    '    prompt: Fix it.',
    '    reference_evidence:',
    '      summary: Real fix updates README punctuation.',
    '      fix_ref: real-fix-ref',
    '      files: [README.md]',
    '    expected_outcome:',
    '      summary: README contains fixed marker.',
    '    hard_evaluation:',
    '      enabled: true',
    '      required_paths: [README.md]',
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
        case_type: 'bugfix',
        prompt: 'Fix it.',
        repo_ref: 'main',
        category: 'runtime',
        difficulty: 'easy',
        validation_commands: ['python -m pytest'],
        reference_evidence: {
          summary: 'Real fix updates README punctuation.',
          fix_ref: 'real-fix-ref',
          files: ['README.md'],
          notes: ['Review only.'],
        },
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
          mode: 'runner',
          max_score: 10,
          runner_agent: null,
          rubric: [],
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

const environmentPayload = {
  ok: true,
  checks: [
    { id: 'git', label: 'Git', status: 'ok', summary: 'git version test', detail: null },
    { id: 'codex', label: 'Codex CLI', status: 'warning', summary: 'codex unavailable in test', detail: null },
    { id: 'repo', label: '项目仓库', status: 'ok', summary: 'Git 仓库可用', detail: null },
  ],
  repo: {
    path: './fixture-repo',
    is_git_repo: true,
    branch: 'main',
    head: 'abc123',
    dirty_file_count: 0,
  },
};

afterEach(() => {
  window.localStorage.clear();
  vi.unstubAllGlobals();
});

function openConfigEditors() {
  const toggle = screen.getByTestId('config-editors-toggle');
  const workbench = toggle.closest('details');
  if (!workbench?.hasAttribute('open')) {
    fireEvent.click(toggle);
  }
}

describe('App workflow shell', () => {
  it('renders deterministic fixture fallback when the local server is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('no server')));

    render(<App />);

    expect(screen.getByTestId('local-app-shell')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'AGENTS.md / skills 效果对比' })).toBeVisible();
    expect(screen.getByText(/同一批题目，换不同 AGENTS.md/)).toBeVisible();
    await waitFor(() => expect(screen.getAllByText('示例数据预览').length).toBeGreaterThan(0));
    expect(screen.getByTestId('codex-run-console')).toBeVisible();
    expect(screen.getByTestId('codex-next-action')).toHaveTextContent('切换到 Codex CLI');
    openConfigEditors();
    expect(screen.getAllByRole('heading', { name: '1 写评测题目' }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('heading', { name: '2 准备对比资料' }).length).toBeGreaterThan(0);
    expect(screen.getByText(/一套方案就是运行时给 AI 看的资料/)).toBeVisible();
    expect(screen.getByText(/同路径会覆盖，如 AGENTS\.md/)).toBeVisible();
    expect(screen.getAllByRole('heading', { name: '3 选择本地 AI' }).length).toBeGreaterThan(0);
    expect(screen.getByLabelText('启动参数')).toBeVisible();
    expect(screen.queryByLabelText('执行器命令模板')).toBeNull();
    expect(screen.queryByRole('heading', { name: '4 设置评分依据' })).toBeNull();
    expect(screen.queryByRole('region', { name: '指标与反馈配置' })).toBeNull();
    expect(screen.getAllByRole('heading', { name: '4 开始评测' }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('heading', { name: '5 看结果和反馈' }).length).toBeGreaterThan(0);
    expect(screen.getByRole('navigation', { name: '工作台导航' })).toBeVisible();
    expect(screen.queryByRole('link', { name: '评分依据' })).toBeNull();
    expect(screen.getByTestId('matrix-count')).toHaveTextContent('8');
    fireEvent.click(screen.getByText('更多设置：自动检查 / 题目信息'));
    fireEvent.click(screen.getByText('配置与任务细节'));
    expect(screen.getByRole('heading', { name: '本地 AI 命令' })).toBeVisible();
    expect(screen.getByRole('heading', { name: '期望结果' })).toBeVisible();
    expect(screen.getByRole('heading', { name: '硬性检查' })).toBeVisible();
    expect(screen.getByRole('heading', { name: 'AI 仲裁' })).toBeVisible();
    expect(screen.getAllByText(/同一个本地 AI/).length).toBeGreaterThan(0);
  });

  it('loads Coco hybrid evaluation data from the local server API', async () => {
    const fetchMock = vi.fn((url: string | URL | Request) => {
      const target = String(url);
      if (target.startsWith('/api/environment')) {
        return jsonResponse(environmentPayload);
      }
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
    await waitFor(() => expect(screen.getByRole('heading', { name: '打开或切换评测项目' })).toBeVisible());
    expect(screen.getByTestId('codex-run-console')).toBeVisible();
    expect(screen.getByLabelText('本地仓库路径')).toHaveValue('./fixture-repo');
    expect(screen.getByText('从 Git URL 克隆')).toBeVisible();
    await waitFor(() => expect(screen.getByLabelText('仓库路径')).toHaveValue('./fixture-repo'));
    openConfigEditors();
    const taskTab = screen.getByRole('button', { name: /Fix greeting punctuation/ });
    expect(within(taskTab).getByText('Fix greeting punctuation')).toBeVisible();
    expect(within(taskTab).getByText('ID: fix-greeting-punctuation')).toBeVisible();
    expect(screen.getByRole('radiogroup', { name: '题目类型' })).toBeVisible();
    expect(
      screen.getByLabelText('题目名称').compareDocumentPosition(screen.getByRole('radiogroup', { name: '题目类型' })) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.getByRole('radio', { name: '修 Bug' })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByLabelText('起始版本')).toHaveValue('main');
    expect(screen.getByLabelText('真实结果 / 修复说明')).toHaveValue('Real fix updates README punctuation.');
    expect(screen.getByText('AI 工作说明')).toBeVisible();
    expect(
      screen.getAllByText('coco -y --query-timeout 10m --bash-tool-timeout 5m -p "{prompt}"').length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText('README contains fixed marker.').length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: '加载配置' }));
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/config/load',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('can clone a Git URL from the first-run setup panel', async () => {
    const fetchMock = vi.fn((url: string | URL | Request, init?: RequestInit) => {
      const target = String(url);
      if (target.startsWith('/api/environment')) {
        return jsonResponse(environmentPayload);
      }
      if (target === '/api/health') {
        return jsonResponse({
          ok: true,
          workspace: {
            state: 'empty',
            has_config: false,
            default_config_path: 'context-eval.yaml',
          },
        });
      }
      if (target === '/api/workspace/project') {
        const body = JSON.parse(String(init?.body || '{}'));
        expect(body).toMatchObject({
          repo_url: 'file:///tmp/SeriaServer.git',
          clone_dir: 'SeriaServer',
          overwrite: false,
        });
        return jsonResponse({
          ok: true,
          state: 'configured',
          has_config: true,
          default_config_path: 'context-eval.yaml',
          config_path: 'context-eval.yaml',
          tasks_path: 'tasks.yaml',
          loaded: {
            ...loadedPayload,
            resolved: { ...loadedPayload.resolved, repo_path: './repositories/SeriaServer' },
          },
        });
      }
      throw new Error(`unexpected request: ${target}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getByRole('heading', { name: '打开评测项目' })).toBeVisible());
    expect(screen.getByRole('heading', { name: '本机检查' })).toBeVisible();
    expect(screen.getByText('Codex CLI')).toBeVisible();

    fireEvent.change(screen.getByLabelText('Git URL'), {
      target: { value: 'file:///tmp/SeriaServer.git' },
    });
    fireEvent.change(screen.getByLabelText('本地文件夹名'), {
      target: { value: 'SeriaServer' },
    });
    fireEvent.click(screen.getByRole('button', { name: '克隆并创建配置' }));

    await waitFor(() => expect(screen.getByTestId('codex-run-console')).toBeVisible());
    openConfigEditors();
    expect(screen.getByRole('heading', { name: '1 写评测题目' })).toBeVisible();
    expect(screen.getAllByText(/仓库已克隆/).length).toBeGreaterThan(0);
  });

  it('submits raw task YAML unknown fields when saving', async () => {
    const tasksWithUnknown = loadedPayload.tasks_yaml.replace(
      '    prompt: Fix it.',
      '    prompt: Fix it.\n    x_unknown_task_field: keep-me',
    );
    const fetchMock = vi.fn((url: string | URL | Request, init?: RequestInit) => {
      const target = String(url);
      if (target.startsWith('/api/environment')) {
        return jsonResponse(environmentPayload);
      }
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
            reference_evidence: {
              ...loadedPayload.editable.tasks[0].reference_evidence,
              summary: 'Visual reference evidence.',
              fix_ref: 'visual-fix-ref',
            },
          },
        ],
      },
    };
    const fetchMock = vi.fn((url: string | URL | Request, init?: RequestInit) => {
      const target = String(url);
      if (target.startsWith('/api/environment')) {
        return jsonResponse(environmentPayload);
      }
      if (target === '/api/health') {
        return jsonResponse({ ok: true, initial_config_path: 'context-eval.yaml' });
      }
      if (target === '/api/config/load') {
        return jsonResponse(loadedPayload);
      }
      if (target === '/api/config/save-editable') {
        const body = JSON.parse(String(init?.body));
        expect(String(init?.body)).toContain('Use the visual editor prompt.');
        expect(String(init?.body)).toContain('Visual editor summary.');
        expect(String(init?.body)).toContain('Visual reference evidence.');
        expect(String(init?.body)).toContain('visual-fix-ref');
        expect(String(init?.body)).toContain('readme-marker');
        expect(body.editable.tasks[0].soft_evaluation.mode).toBe('runner');
        expect(body.editable.tasks[0].soft_evaluation.runner_agent).toBeNull();
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
              case_type: 'bugfix',
              reference_evidence_summary: 'Visual reference evidence.',
              command_preview: 'coco -p prompt',
              expected_outcome_summary: 'Visual editor summary.',
              hard_evaluation_enabled: true,
              soft_evaluation_enabled: true,
              soft_evaluation_mode: 'runner',
              soft_evaluation_runner_agent: null,
            },
          ],
        });
      }
      throw new Error(`unexpected request: ${target}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getByLabelText('发给 AI 的任务提示词')).toHaveValue('Fix it.'));
    openConfigEditors();
    expect(screen.getByRole('radiogroup', { name: '题目类型' })).toBeVisible();
    expect(screen.getByRole('radio', { name: '修 Bug' })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByLabelText('起始版本')).toHaveValue('main');
    fireEvent.click(screen.getByText('更多设置：自动检查 / 题目信息'));
    expect(screen.getAllByRole('radiogroup', { name: '任务分类' }).length).toBeGreaterThan(0);
    expect(
      screen.getAllByRole('radio', { name: '运行时' }).some((node) => node.getAttribute('aria-checked') === 'true'),
    ).toBe(true);
    expect(screen.getAllByRole('radiogroup', { name: '难度' }).length).toBeGreaterThan(0);
    expect(
      screen.getAllByRole('radio', { name: '简单' }).some((node) => node.getAttribute('aria-checked') === 'true'),
    ).toBe(true);
    fireEvent.change(screen.getByLabelText('发给 AI 的任务提示词'), {
      target: { value: 'Use the visual editor prompt.' },
    });
    fireEvent.change(screen.getByLabelText('期望结果'), {
      target: { value: 'Visual editor summary.' },
    });
    fireEvent.change(screen.getByLabelText('真实结果 / 修复说明'), {
      target: { value: 'Visual reference evidence.' },
    });
    fireEvent.change(screen.getByLabelText('真实修复版本'), {
      target: { value: 'visual-fix-ref' },
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
    fireEvent.click(screen.getByRole('button', { name: '保存评测题目' }));

    await waitFor(() => expect(screen.getByTestId('task-save-status')).toHaveTextContent('已保存评测题目并刷新评测计划'));
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
            command: 'coco -y --query-timeout 5m --bash-tool-timeout 5m -p "{prompt}"',
            timeout_minutes: 15,
            network: 'enabled',
          },
        ],
        agent: {
          ...loadedPayload.editable.agent,
          command: 'coco -y --query-timeout 5m --bash-tool-timeout 5m -p "{prompt}"',
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
      if (target.startsWith('/api/environment')) {
        return jsonResponse(environmentPayload);
      }
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
        expect(body.editable.agents[0].command).toBe('coco -y --query-timeout 5m --bash-tool-timeout 5m -p "{prompt}"');
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

    await waitFor(() => expect(screen.getByLabelText('资料包名称')).toHaveValue('Baseline'));
    openConfigEditors();
    fireEvent.change(screen.getByLabelText('资料包名称'), {
      target: { value: 'Edited baseline instructions' },
    });
    fireEvent.change(screen.getByLabelText('资料来源路径 1'), {
      target: { value: './contexts/edited/AGENTS.md' },
    });
    fireEvent.change(screen.getByLabelText('启动参数'), {
      target: { value: '--query-timeout 5m --bash-tool-timeout 5m' },
    });
    fireEvent.change(screen.getByLabelText('执行器超时分钟'), {
      target: { value: '15' },
    });
    fireEvent.change(screen.getByLabelText('执行器联网权限'), {
      target: { value: 'enabled' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存对比资料' }));

    await waitFor(() => {
      expect(screen.getByTestId('variant-save-status')).toHaveTextContent('已保存配置并刷新评测计划');
    });
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/config/save-editable',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/run-plan',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(screen.getByLabelText('资料包名称')).toHaveValue('Edited baseline instructions');
  });

  it('blocks invalid task fields before submitting structured saves', async () => {
    const fetchMock = vi.fn((url: string | URL | Request) => {
      const target = String(url);
      if (target.startsWith('/api/environment')) {
        return jsonResponse(environmentPayload);
      }
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

    await waitFor(() => expect(screen.getByLabelText('发给 AI 的任务提示词')).toHaveValue('Fix it.'));
    openConfigEditors();
    fireEvent.change(screen.getByLabelText('发给 AI 的任务提示词'), { target: { value: ' ' } });
    fireEvent.change(screen.getByLabelText('命令 1'), { target: { value: ' ' } });
    fireEvent.click(screen.getByRole('button', { name: '保存评测题目' }));

    const taskPanel = screen.getByRole('region', { name: '测试用例配置' });
    expect(await within(taskPanel).findByText('fix-greeting-punctuation: 任务提示词不能为空')).toBeVisible();
    expect(within(taskPanel).getByText('fix-greeting-punctuation: 第 1 条验证命令不能为空')).toBeVisible();
    expect(within(taskPanel).getByTestId('task-save-status')).toHaveTextContent(
      '有配置问题，请按红色提示修改后再保存',
    );
    expect(document.querySelector('.scope-notice')).toBeNull();
    expect(fetchMock).not.toHaveBeenCalledWith(
      '/api/config/save-editable',
      expect.anything(),
    );
  });

  it('blocks invalid variant and agent fields before structured saves', async () => {
    const fetchMock = vi.fn((url: string | URL | Request) => {
      const target = String(url);
      if (target.startsWith('/api/environment')) {
        return jsonResponse(environmentPayload);
      }
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

    await waitFor(() => expect(screen.getByLabelText('资料包 ID')).toHaveValue('baseline'));
    openConfigEditors();
    fireEvent.change(screen.getByLabelText('资料包 ID'), { target: { value: ' ' } });
    fireEvent.change(screen.getByLabelText('资料来源路径 1'), { target: { value: ' ' } });
    fireEvent.change(screen.getByLabelText('执行器类型'), { target: { value: 'custom' } });
    fireEvent.click(screen.getByText('高级：技术命令（不推荐）'));
    fireEvent.change(screen.getByLabelText('自定义完整命令'), { target: { value: ' ' } });
    fireEvent.change(screen.getByLabelText('执行器超时分钟'), { target: { value: '0' } });
    await waitFor(() => expect(screen.getByLabelText('资料包 ID')).toHaveValue(' '));
    await waitFor(() => expect(screen.getByLabelText('执行器超时分钟')).toHaveValue(0));
    fireEvent.click(screen.getByRole('button', { name: '保存本地 AI 配置' }));

    const variantPanel = screen.getByRole('region', { name: '对比资料配置' });
    const agentPanel = screen.getByRole('region', { name: '执行器配置' });
    expect(await within(variantPanel).findByText('第 1 套对比资料名称不能为空')).toBeVisible();
    expect(within(variantPanel).getByText('第 1 套对比资料的第 1 份资料来源路径不能为空')).toBeVisible();
    expect(within(agentPanel).getByText('第 1 个本地 AI命令不能为空')).toBeVisible();
    expect(within(agentPanel).getByText('第 1 个本地 AI最长运行时间必须大于 0')).toBeVisible();
    expect(within(agentPanel).getByTestId('agent-save-status')).toHaveTextContent(
      '有配置问题，请按红色提示修改后再保存',
    );
    expect(document.querySelector('.scope-notice')).toBeNull();
    expect(fetchMock).not.toHaveBeenCalledWith(
      '/api/config/save-editable',
      expect.anything(),
    );
  });

  it('saves codex-cli agents with codex-jsonl telemetry', async () => {
    const fetchMock = vi.fn((url: string | URL | Request, init?: RequestInit) => {
      const target = String(url);
      if (target.startsWith('/api/environment')) {
        return jsonResponse(environmentPayload);
      }
      if (target === '/api/health') {
        return jsonResponse({ ok: true, initial_config_path: 'context-eval.yaml' });
      }
      if (target === '/api/config/load') {
        return jsonResponse(loadedPayload);
      }
      if (target === '/api/config/save-editable') {
        const body = JSON.parse(String(init?.body));
        expect(body.editable.agent.kind).toBe('codex-cli');
        expect(body.editable.agent.telemetry).toEqual({
          collector: 'codex-jsonl',
          file: 'codex-events.jsonl',
        });
        expect(body.editable.agents[0].telemetry).toEqual({
          collector: 'codex-jsonl',
          file: 'codex-events.jsonl',
        });
        return jsonResponse({ ok: true, reloaded: loadedPayload });
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
          cases: [],
          codex_profile_diagnostics: [],
        });
      }
      throw new Error(`unexpected request: ${target}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getByLabelText('执行器类型')).toHaveValue('coco'));
    fireEvent.change(screen.getByLabelText('执行器类型'), { target: { value: 'codex-cli' } });
    fireEvent.click(screen.getByRole('button', { name: '保存本地 AI 配置' }));

    await waitFor(() => {
      expect(screen.getByTestId('agent-save-status')).toHaveTextContent('已保存配置并刷新评测计划');
    });
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
      if (target.startsWith('/api/environment')) {
        return jsonResponse(environmentPayload);
      }
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

    await waitFor(() => expect(screen.getByLabelText('评测题目 second-task')).toBeChecked());
    fireEvent.click(screen.getByLabelText('评测题目 fix-greeting-punctuation'));
    fireEvent.click(screen.getByLabelText('对比资料 baseline'));
    fireEvent.click(screen.getByLabelText('本地 AI coco'));
    fireEvent.click(screen.getByRole('button', { name: '刷新评测计划' }));

    await waitFor(() => expect(screen.getByTestId('planned-case-count')).toHaveTextContent('1'));
    expect(screen.getByText('second-task__experiment__codex')).toBeVisible();

    fireEvent.click(screen.getByRole('button', { name: '开始评测' }));
    await waitFor(() => expect(screen.getByTestId('run-status')).toHaveTextContent('已完成 1/1'));
    expect(screen.getAllByText('codex').length).toBeGreaterThan(0);
  });

  it('shows API errors from structured saves', async () => {
    const fetchMock = vi.fn((url: string | URL | Request) => {
      const target = String(url);
      if (target.startsWith('/api/environment')) {
        return jsonResponse(environmentPayload);
      }
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

    await waitFor(() => expect(screen.getByLabelText('发给 AI 的任务提示词')).toHaveValue('Fix it.'));
    fireEvent.click(screen.getByRole('button', { name: '保存评测题目' }));

    await waitFor(() => {
      expect(screen.getByText('错误: tasks.0.prompt: server validation failed')).toBeVisible();
    });
  });

  it('shows hard and soft result status after a completed run', async () => {
    const fetchMock = vi.fn((url: string | URL | Request) => {
      const target = String(url);
      if (target.startsWith('/api/environment')) {
        return jsonResponse(environmentPayload);
      }
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
          baseline_selection_notice: requestedBaseline === 'removed' ? '已清理不存在的对照组方案 removed，改用 baseline。' : null,
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
              mode: 'runner',
              meaning: 'soft evaluation 默认使用同一个本地 AI 输出软评分。',
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
              soft_evaluation_status: 'result_available',
              soft_evaluation_payload_path:
                'artifacts/fix-greeting-punctuation__baseline__coco/soft_evaluation_payload.json',
              soft_evaluation_result_path:
                'artifacts/fix-greeting-punctuation__baseline__coco/soft_evaluation_result.json',
              soft_evaluation_runner_agent: 'judge',
              soft_evaluation_score: 8,
              soft_evaluation_max_score: 10,
              soft_evaluation_verdict: 'pass',
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
            soft_evaluation_status: 'result_available',
            soft_evaluation_payload_path:
              'artifacts/fix-greeting-punctuation__baseline__coco/soft_evaluation_payload.json',
            soft_evaluation_result_path:
              'artifacts/fix-greeting-punctuation__baseline__coco/soft_evaluation_result.json',
            soft_evaluation_runner_agent: 'judge',
            soft_evaluation_score: 8,
            soft_evaluation_max_score: 10,
            soft_evaluation_verdict: 'pass',
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
            status: 'result_available',
            payload_path: 'artifacts/fix-greeting-punctuation__baseline__coco/soft_evaluation_payload.json',
            result_path: 'artifacts/fix-greeting-punctuation__baseline__coco/soft_evaluation_result.json',
            runner_agent: 'judge',
            score: 8,
            max_score: 10,
            verdict: 'pass',
          },
          manual_review: {
            case_id: 'fix-greeting-punctuation__baseline__coco',
            decision: 'not_reviewed',
            confidence: 'unknown',
            rating: null,
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
            rating: 5,
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
    fireEvent.click(screen.getByRole('button', { name: '开始评测' }));
    await waitFor(() => expect(screen.getByTestId('preflight-status')).toHaveTextContent('运行前检查通过'));
    await waitFor(() => expect(screen.getByTestId('planned-case-count')).toHaveTextContent('1'));
    expect(screen.queryByRole('button', { name: '运行预检' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '生成矩阵' })).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText('通过 4/4').length).toBeGreaterThan(0));
    expect(screen.getByText('评测结果已生成')).toBeVisible();
    expect(screen.getByRole('button', { name: '查看结果和反馈' })).toBeVisible();
    expect(screen.getAllByText(/8\/10/).length).toBeGreaterThan(0);
    expect(screen.getByText('AI 仲裁执行器')).toBeVisible();
    expect(screen.getByText('judge')).toBeVisible();
    expect(screen.getByText('先看结论，再看证据')).toBeVisible();
    expect(screen.getByLabelText('对照方案')).toHaveValue('baseline');
    expect(screen.getByText('对比对象改善')).toBeVisible();
    expect(screen.getByText('对比对象 hard evaluation 增加 1，validation 结果未变化。')).toBeVisible();
    expect(screen.getByText('Patch')).toBeVisible();
    expect(screen.getAllByText('patches/fix-greeting-punctuation__baseline__coco.patch').length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText('对照方案'), { target: { value: 'experiment' } });
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/results?run_dir=.%2Fruns%2Frun-a&baseline_variant=experiment',
        expect.any(Object),
      ),
    );

    fireEvent.click(screen.getByRole('button', { name: '查看变更和日志' }));
    await waitFor(() => expect(screen.getByRole('heading', { name: '变更与打分材料' })).toBeVisible());
    expect(screen.getAllByText('patches/fix-greeting-punctuation__baseline__coco.patch').length).toBeGreaterThan(0);
    expect(screen.getByText(/context-eval marker/)).toBeVisible();
    expect(screen.getByRole('heading', { name: '硬性检查明细' })).toBeVisible();
    expect(screen.getByText('found expected marker')).toBeVisible();
    expect(screen.getByLabelText('软性复核材料')).toHaveTextContent('8/10');
    expect(screen.getByLabelText('软性复核材料')).toHaveTextContent('judge');
    expect(screen.getByLabelText('软性复核材料')).toHaveTextContent('soft_evaluation_result.json');
    expect(screen.getByTestId('codex-usage-panel')).toBeInTheDocument();
    expect(screen.getByText('Codex CLI 硬指标（JSONL）')).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Codex 使用画像' })).toBeVisible();
    expect(screen.getAllByText('27').length).toBeGreaterThan(0);
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
    fireEvent.change(screen.getByLabelText('人工评分'), { target: { value: '5' } });
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
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/manual-review',
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('"rating":5'),
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
