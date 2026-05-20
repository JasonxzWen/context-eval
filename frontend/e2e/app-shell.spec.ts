import { expect, test, type Page, type Route } from '@playwright/test';
import { spawn, spawnSync, type ChildProcessWithoutNullStreams } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const e2eDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(e2eDir, '..');
const repoRoot = path.resolve(frontendDir, '..');
const python = process.env.CONTEXT_EVAL_PYTHON || process.env.PYTHON || 'python';

function toPosix(value: string) {
  return value.replace(/\\/g, '/');
}

function run(command: string, args: string[], cwd: string) {
  const result = spawnSync(command, args, {
    cwd,
    encoding: 'utf-8',
    env: { ...process.env, PYTHONUTF8: '1' },
  });
  if (result.status !== 0) {
    throw new Error(
      `command failed: ${command} ${args.join(' ')}\nstdout:\n${result.stdout}\nstderr:\n${result.stderr}`,
    );
  }
}

async function fulfillJson(route: Route, data: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json; charset=utf-8',
    body: JSON.stringify(data),
  });
}

function copyFixtureRepo(workspace: string) {
  const source = path.join(repoRoot, 'examples', 'fixture-repo');
  const fixture = path.join(workspace, 'fixture-repo');
  fs.cpSync(source, fixture, {
    recursive: true,
    filter: (sourcePath) =>
      !sourcePath.includes(`${path.sep}.git`) &&
      !sourcePath.includes(`${path.sep}__pycache__`) &&
      !sourcePath.includes(`${path.sep}.pytest_cache`),
  });
  run(python, ['setup_fixture_repo.py'], fixture);
  return fixture;
}

function writeWorkflowFiles(workspace: string, fixture: string) {
  const baselineContextDir = path.join(workspace, 'contexts', 'baseline');
  const experimentContextDir = path.join(workspace, 'contexts', 'experiment');
  const agentScript = path.join(workspace, 'fake-coco.py');
  fs.mkdirSync(baselineContextDir, { recursive: true });
  fs.mkdirSync(experimentContextDir, { recursive: true });
  fs.writeFileSync(path.join(baselineContextDir, 'AGENTS.md'), '# Browser workflow instructions\n');
  fs.writeFileSync(path.join(experimentContextDir, 'AGENTS.md'), '# Browser workflow experiment instructions\n');
  fs.writeFileSync(
    agentScript,
    [
      'from pathlib import Path',
      'p = Path("fixture_app/greetings.py")',
      'text = p.read_text(encoding="utf-8")',
      'p.write_text(',
      '    text.replace(',
      '        \'return f"Hello, {name}"\',',
      '        \'return f"Hello, {name}!"  # context-eval\',',
      '    ),',
      '    encoding="utf-8",',
      ')',
      '',
    ].join('\n'),
  );
  fs.writeFileSync(
    path.join(workspace, 'tasks.yaml'),
    [
      'tasks:',
      '  - id: fix-greeting-punctuation',
      '    title: Fix greeting punctuation',
      '    prompt: Fix the fixture greeting punctuation.',
      '    category: runtime',
      '    difficulty: easy',
      '    expected_outcome:',
      '      summary: Greeting uses context-eval wording.',
      '      acceptance_points:',
      '        - Greeting output changes.',
      '    hard_evaluation:',
      '      enabled: true',
      '      required_paths:',
      '        - fixture_app/greetings.py',
      '      expected_snippets:',
      '        - path: fixture_app/greetings.py',
      '          snippets:',
      '            - context-eval',
      '    soft_evaluation:',
      '      enabled: true',
      '      mode: payload-only',
      '      rubric:',
      '        - name: quality',
      '          weight: 1',
      '          description: Patch is clear.',
      '',
    ].join('\n'),
  );
  fs.writeFileSync(
    path.join(workspace, 'context-eval.yaml'),
    [
      'repo:',
      `  path: "${toPosix(fixture)}"`,
      '  base_ref: main',
      'agents:',
      '  coco:',
      '    kind: coco',
      `    command: '"${toPosix(python)}" "${toPosix(agentScript)}"'`,
      '    timeout_minutes: 1',
      '    network: disabled',
      'tasks: ./tasks.yaml',
      'output_dir: ./runs',
      'variants:',
      '  baseline:',
      '    description: Browser workflow baseline',
      '    overlays:',
      '      - source: ./contexts/baseline/AGENTS.md',
      '        target: AGENTS.md',
      '  experiment:',
      '    description: Browser workflow experiment',
      '    overlays:',
      '      - source: ./contexts/experiment/AGENTS.md',
      '        target: AGENTS.md',
      'evaluation:',
      `  commands: ['"${toPosix(python)}" -m pytest']`,
      '',
    ].join('\n'),
  );
}

async function expectNoHorizontalOverflow(page: Page) {
  const overflowReport = await page.evaluate(() => {
    const viewportWidth = document.documentElement.clientWidth;
    const pageWidth = document.documentElement.scrollWidth;
    const offenders = Array.from(document.querySelectorAll<HTMLElement>('body *'))
      .map((element) => {
        const rect = element.getBoundingClientRect();
        const style = window.getComputedStyle(element);
        const parentChain = [];
        let parent = element.parentElement;
        while (parent && parentChain.length < 5) {
          parentChain.push(
            `${parent.tagName.toLowerCase()}${parent.className ? `.${String(parent.className).replace(/\s+/g, '.')}` : ''}`,
          );
          parent = parent.parentElement;
        }
        return {
          tag: element.tagName.toLowerCase(),
          className: String(element.className || ''),
          testId: element.getAttribute('data-testid') || '',
          display: style.display,
          minWidth: style.minWidth,
          maxWidth: style.maxWidth,
          overflowWrap: style.overflowWrap,
          text: (element.textContent || '').trim().slice(0, 80),
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          width: Math.round(rect.width),
          parentChain,
        };
      })
      .filter((item) => item.right > viewportWidth + 1 || item.left < -1)
      .sort((a, b) => b.right - a.right)
      .slice(0, 8);
    return {
      hasOverflow: pageWidth > viewportWidth + 1,
      pageWidth,
      viewportWidth,
      offenders,
    };
  });
  expect(overflowReport.hasOverflow, JSON.stringify(overflowReport, null, 2)).toBe(false);
}

async function expectNoVerticalButtonText(page: Page) {
  const verticalButtons = await page.evaluate(() => Array.from(document.querySelectorAll('button'))
    .map((button) => {
      const rect = button.getBoundingClientRect();
      const text =
        button.innerText.trim() ||
        button.textContent?.trim() ||
        button.getAttribute('aria-label') ||
        '';
      return {
        text,
        width: rect.width,
        height: rect.height,
        ratio: rect.height / Math.max(rect.width, 1),
      };
    })
    .filter((item) => item.text && item.width > 0 && item.height > 0 && item.ratio > 2.8));
  expect(verticalButtons).toEqual([]);
}

async function startLocalApp(workspace: string, options: { config?: string | null } = { config: 'context-eval.yaml' }) {
  const args = [
    '-m',
    'context_eval',
    'app',
    '--workspace',
    workspace,
    '--port',
    '0',
  ];
  if (options.config) {
    args.splice(5, 0, '--config', options.config);
  }
  const child = spawn(
    python,
    args,
    {
      cwd: repoRoot,
      env: { ...process.env, PYTHONUTF8: '1' },
    },
  );

  return await new Promise<{ child: ChildProcessWithoutNullStreams; url: string }>(
    (resolve, reject) => {
      const timer = setTimeout(() => {
        child.kill();
        reject(new Error('local app server did not print a URL'));
      }, 20000);
      let output = '';
      const onData = (chunk: Buffer) => {
        output += chunk.toString();
        const match = output.match(/http:\/\/127\.0\.0\.1:\d+/);
        if (match) {
          clearTimeout(timer);
          resolve({ child, url: match[0] });
        }
      };
      child.stdout.on('data', onData);
      child.stderr.on('data', onData);
      child.on('exit', (code) => {
        clearTimeout(timer);
        reject(new Error(`local app server exited early with ${code}\n${output}`));
      });
    },
  );
}

test('empty workspace starts at first-run choices and bootstraps demo', async ({ page }) => {
  test.setTimeout(90_000);
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'context-eval-empty-app-'));
  const server = await startLocalApp(workspace, { config: null });

  try {
    await page.goto(server.url);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: 'context-eval 本地工作台' })).toBeVisible();
    await expect(page.getByRole('heading', { name: '开始使用' })).toBeVisible();
    await expect(page.getByText('./fixture-repo')).toHaveCount(0);

    await page.getByRole('button', { name: '试用示例' }).click();
    await expect(page.getByLabel('仓库路径')).toHaveValue('./demo-repo');

    await expect(page.locator('.run-brief-panel')).toContainText('baseline vs experiment');
    await expect(page.getByRole('heading', { name: '评测任务编辑器' })).toBeVisible();
    await expect(page.getByRole('radiogroup', { name: '任务分类' })).toBeVisible();
    await expect(page.getByRole('radio', { name: '缺陷修复' })).toHaveAttribute('aria-checked', 'true');
    await expect(page.getByRole('radio', { name: '简单' })).toHaveAttribute('aria-checked', 'true');
    await page.getByLabel('期望结果摘要').fill('Visual editor saved summary.');
    await page.getByRole('button', { name: '保存任务' }).click();
    await expect(page.getByTestId('task-save-status')).toContainText('已保存任务并刷新执行计划');
    await expect(page.locator('.matrix-panel')).toContainText('Visual editor saved summary.');

    await page.getByLabel('选择上下文版本 experiment').click();
    await page.getByLabel('版本说明').fill('Edited experiment instructions');
    await page.getByLabel('执行器超时分钟').fill('3');
    await page.getByRole('button', { name: '保存执行器配置' }).click();
    await expect(page.getByTestId('agent-save-status')).toContainText('已保存配置并刷新执行计划');
    await expect(page.getByLabel('执行器超时分钟')).toHaveValue('3');
    await page.getByRole('button', { name: '保存上下文版本' }).click();
    await expect(page.getByTestId('variant-save-status')).toContainText('已保存配置并刷新执行计划');
    await expect(page.getByLabel('版本说明')).toHaveValue('Edited experiment instructions');

    await page.getByRole('checkbox', { name: '上下文版本 baseline' }).uncheck();
    await page.getByRole('button', { name: '刷新执行计划' }).click();
    await expect(page.getByTestId('planned-case-count')).toHaveText('1');

    await page.getByRole('button', { name: '开始运行' }).click();
    await expect(page.getByTestId('preflight-status')).toContainText('运行前检查通过');
    await expect(page.getByTestId('planned-case-count')).toHaveText('1');
    await expect(page.getByTestId('run-status')).toContainText('已完成', { timeout: 60000 });
    await expect(page.getByText('结果已生成')).toBeVisible();
    await expect(page.getByRole('cell', { name: '通过 4/4' })).toBeVisible();

    const experimentRow = page.locator('tbody tr', { hasText: 'experiment' });
    await experimentRow.getByRole('button').click();
    await expect(page.getByRole('heading', { name: '用例详情' })).toBeVisible();
    await expect(page.locator('.case-detail-panel')).toContainText('experiment');
    await expect(page.locator('.artifact-pane').first()).toBeVisible();

    await page.getByLabel('复核结论').selectOption('pass');
    await page.getByLabel('复核可信度').selectOption('high');
    await page.getByLabel('复核人').fill('manual');
    await page.getByLabel('复核备注').fill('Experiment result accepted.');
    await page.locator('.review-form button[type="submit"]').click();
    await expect(page.locator('.review-form .status-line')).toContainText('复核');

    await page.getByRole('button', { name: /JSON/ }).click();
    await expect(page.getByTestId('export-output')).toContainText('"manual_reviews"');
    await expect(page.getByTestId('export-output')).toContainText('"decision": "pass"');
  } finally {
    await stopLocalApp(server.child);
    fs.rmSync(workspace, { recursive: true, force: true });
  }
});

test('empty workspace can open a real local project and surfaces bad project paths', async ({
  page,
}) => {
  test.setTimeout(90_000);
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'context-eval-project-app-'));
  const fixture = copyFixtureRepo(workspace);
  const server = await startLocalApp(workspace, { config: null });

  try {
    await page.goto(server.url);
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('heading', { name: '开始使用' })).toBeVisible();

    await page.getByLabel('项目路径').fill(path.join(workspace, 'missing-repo'));
    await page.getByRole('button', { name: '创建工作区' }).click();
    await expect(page.getByText('错误: repo path does not exist')).toBeVisible();

    await page.getByLabel('项目路径').fill(fixture);
    await page.getByRole('button', { name: '创建工作区' }).click();
    await expect(page.getByRole('heading', { name: '评测任务编辑器' })).toBeVisible();
    await page.getByText('配置与任务细节').click();
    await expect(page.getByLabel('仓库路径')).toHaveValue(toPosix(fixture));
    await expect(page.getByLabel('配置路径')).toHaveValue(/context-eval\.yaml$/);
    await expectNoHorizontalOverflow(page);
    await expectNoVerticalButtonText(page);
  } finally {
    await stopLocalApp(server.child);
    fs.rmSync(workspace, { recursive: true, force: true });
  }
});

test('structured editors copy, delete, save, and reject unsafe overlay paths', async ({
  page,
}) => {
  test.setTimeout(90_000);
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'context-eval-editor-app-'));
  const server = await startLocalApp(workspace, { config: null });

  try {
    await page.goto(server.url);
    await page.getByRole('button', { name: '试用示例' }).click();
    await expect(page.getByRole('heading', { name: '评测任务编辑器' })).toBeVisible();

    const variantPanel = page.getByLabel('上下文版本配置');
    await variantPanel.getByRole('button', { name: '复制' }).click();
    await expect(variantPanel.getByLabel('版本名称')).toHaveValue('baseline-copy');
    await variantPanel.getByLabel('覆盖文件目标路径 1').fill('../AGENTS.md');
    await variantPanel.getByRole('button', { name: '保存上下文版本' }).click();
    const unsafeTargetError =
      '错误: export blocked: variant 3 overlay 1 target must be a safe relative path';
    await expect(page.getByText(unsafeTargetError)).toBeVisible();

    await variantPanel.getByLabel('覆盖文件目标路径 1').fill('docs/AGENTS.md');
    await variantPanel.getByRole('button', { name: '保存上下文版本' }).click();
    await expect(page.getByTestId('variant-save-status')).toContainText('已保存配置并刷新执行计划');
    await expect(page.getByText(unsafeTargetError)).toHaveCount(0);

    page.once('dialog', (dialog) => dialog.accept());
    await variantPanel.getByLabel('上下文版本列表').getByRole('button', { name: '删除' }).click();
    await expect(variantPanel.getByLabel('版本名称')).toHaveValue('experiment');

    const agentPanel = page.getByLabel('执行器配置');
    await agentPanel.getByRole('button', { name: '复制' }).click();
    await expect(agentPanel.getByLabel('执行器名称')).toHaveValue('demo-agent-copy');
    page.once('dialog', (dialog) => dialog.accept());
    await agentPanel.getByRole('button', { name: '删除' }).click();
    await expect(agentPanel.getByLabel('执行器名称')).toHaveValue('demo-agent');
    await expectNoHorizontalOverflow(page);
    await expectNoVerticalButtonText(page);
  } finally {
    await stopLocalApp(server.child);
    fs.rmSync(workspace, { recursive: true, force: true });
  }
});

async function stopLocalApp(child: ChildProcessWithoutNullStreams) {
  if (child.exitCode !== null || child.signalCode !== null) {
    return;
  }
  await new Promise<void>((resolve) => {
    const timer = setTimeout(() => {
      if (child.exitCode === null && child.signalCode === null) {
        child.kill('SIGKILL');
      }
    }, 5000);
    child.once('exit', () => {
      clearTimeout(timer);
      resolve();
    });
    child.kill();
  });
}

test('renders the fixture-backed Coco hybrid shell', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'context-eval 本地工作台' })).toBeVisible();
  await expect(page.getByTestId('matrix-count')).toHaveText('8');
  await page.getByText('配置与任务细节').click();
  await expect(page.getByRole('heading', { name: '执行器', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: '期望结果' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '硬性检查' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '人工评审规则' })).toBeVisible();
  await expect(page.getByRole('button', { name: '加载配置' })).toBeVisible();
  await expect(page.getByRole('button', { name: '保存并重载' })).toBeVisible();

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  );
  expect(hasHorizontalOverflow).toBe(false);
  await expectNoVerticalButtonText(page);
});

test('explains scoring gaps, baseline changes, and API errors in results UI', async ({
  page,
}, testInfo) => {
  const manualReview = {
    case_id: 'fix-greeting__baseline__demo-agent',
    decision: 'not_reviewed',
    confidence: 'unknown',
    reviewer: '',
    notes: '',
    updated_at: null,
  };
  const loadedPayload = {
    ok: true,
    config_path: 'context-eval.yaml',
    tasks_path: 'tasks.yaml',
    config_yaml: 'repo:\n  path: ./demo-repo\n',
    tasks_yaml: 'tasks:\n  - id: fix-greeting\n    prompt: Fix greeting.\n',
    editable: {
      repo: { path: './demo-repo', base_ref: 'main' },
      agent: {
        name: 'demo-agent',
        kind: 'custom',
        command: 'python scripts/example_agent.py "{prompt_file}"',
        timeout_minutes: 2,
        network: 'disabled',
      },
      agent_shape: 'agents',
      agents: [
        {
          name: 'demo-agent',
          kind: 'custom',
          command: 'python scripts/example_agent.py "{prompt_file}"',
          timeout_minutes: 2,
          network: 'disabled',
        },
      ],
      tasks_path: './tasks.yaml',
      variants: [
        { name: 'baseline', description: 'Demo baseline', overlays: [] },
        { name: 'experiment', description: 'Demo experiment', overlays: [] },
      ],
      tasks: [
        {
          id: 'fix-greeting',
          title: 'Fix greeting',
          prompt: 'Fix greeting punctuation.',
          category: 'runtime',
          difficulty: 'easy',
          validation_commands: [],
          expected_outcome: {
            summary: 'Greeting is fixed.',
            acceptance_points: ['Greeting output changes.'],
          },
          hard_evaluation: {
            enabled: true,
            require_validation_pass: false,
            required_paths: ['fixture_app/greetings.py'],
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
      evaluation_commands: [],
      evaluation_timeout_seconds: null,
      output_dir: './runs',
    },
    resolved: {
      repo_path: './demo-repo',
      output_dir: './runs',
      agents: ['demo-agent'],
      variants: ['baseline', 'experiment'],
      tasks: ['fix-greeting'],
    },
  };
  const explanation = {
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
    manual_review: { meaning: 'manual review 是人工复核证据和结论，不是自动评分。' },
    evidence_limits: ['无 validation、hard skipped 或 telemetry missing 时只能提示证据不足。'],
  };
  const baselineCase = {
    case_id: 'fix-greeting__baseline__demo-agent',
    agent_name: 'demo-agent',
    task_id: 'fix-greeting',
    variant: 'baseline',
    status: 'completed',
    validation_status: 'skipped',
    confidence: 'low',
    telemetry_status: 'unavailable',
    telemetry_source: 'none',
    telemetry_error: 'telemetry file not found: artifacts/telemetry.json',
    total_tokens: null,
    reasoning_tokens: null,
    reasoning_step_count: null,
    tool_call_count: null,
    changed_files: 1,
    hard_evaluation_status: 'skipped',
    hard_evaluation_score: null,
    hard_evaluation_max_score: null,
    hard_evaluation_passed_checks: null,
    hard_evaluation_failed_checks: null,
    soft_evaluation_status: 'payload_generated',
    soft_evaluation_payload_path:
      'artifacts/fix-greeting__baseline__demo-agent/soft_evaluation_payload.json',
    patch_path: 'patches/fix-greeting__baseline__demo-agent.patch',
    stdout_path: 'logs/fix-greeting__baseline__demo-agent.stdout.log',
    stderr_path: 'logs/fix-greeting__baseline__demo-agent.stderr.log',
    manual_review: manualReview,
  };
  const experimentCase = {
    ...baselineCase,
    case_id: 'fix-greeting__experiment__demo-agent',
    variant: 'experiment',
    validation_status: 'passed',
    confidence: 'high',
    telemetry_status: 'collected',
    telemetry_source: 'json-file',
    telemetry_error: null,
    total_tokens: 100,
    reasoning_tokens: 12,
    reasoning_step_count: 2,
    tool_call_count: 3,
    hard_evaluation_status: 'passed',
    hard_evaluation_score: 1,
    hard_evaluation_max_score: 1,
    hard_evaluation_passed_checks: 1,
    hard_evaluation_failed_checks: 0,
    soft_evaluation_payload_path:
      'artifacts/fix-greeting__experiment__demo-agent/soft_evaluation_payload.json',
    patch_path: 'patches/fix-greeting__experiment__demo-agent.patch',
    stdout_path: 'logs/fix-greeting__experiment__demo-agent.stdout.log',
    stderr_path: 'logs/fix-greeting__experiment__demo-agent.stderr.log',
  };
  const evidenceGaps = (role: 'baseline' | 'comparison', variant: string) => {
    const roleLabel = role === 'baseline' ? '比较基线' : '对比对象';
    return [
      {
        code: `${role}_validation_missing`,
        variant,
        case_id: `fix-greeting__${variant}__demo-agent`,
        message: `${roleLabel}没有 validation commands，本次不能给高置信判断。`,
        next_step: '为任务配置项目自己的测试或验证脚本后重新运行。',
      },
      {
        code: `${role}_hard_evaluation_skipped`,
        variant,
        case_id: `fix-greeting__${variant}__demo-agent`,
        message: `${roleLabel}的 hard check 被跳过，缺少可评分的确定性证据。`,
        next_step: '保留工作区或补充可从 patch 判断的 hard_evaluation 规则后重新运行。',
      },
      {
        code: `${role}_telemetry_missing`,
        variant,
        case_id: `fix-greeting__${variant}__demo-agent`,
        message: `${roleLabel}缺少结构化 telemetry：telemetry file not found: artifacts/telemetry.json。`,
        next_step: '确认 agent 是否写入本地 telemetry JSON；不要从日志猜测 token 或工具调用。',
      },
    ];
  };
  const resultsPayload = (selectedBaseline: string) => {
    const comparison = selectedBaseline === 'baseline' ? 'experiment' : 'baseline';
    return {
      ok: true,
      run_dir: './runs/browser-acceptance',
      overview: {
        case_count: 2,
        failed_count: 0,
        timeout_count: 0,
        low_confidence_count: 1,
        telemetry_gap_count: 1,
      },
      selected_baseline_variant: selectedBaseline,
      available_baseline_variants: ['baseline', 'experiment'],
      baseline_selection_notice: null,
      evaluation_explanation: explanation,
      compare_groups: [
        {
          group_id: `fix-greeting__demo-agent__trial-1__${selectedBaseline}__vs__${comparison}`,
          task_id: 'fix-greeting',
          agent_name: 'demo-agent',
          trial_index: 1,
          baseline_variant: selectedBaseline,
          comparison_variant: comparison,
          baseline_case_id: `fix-greeting__${selectedBaseline}__demo-agent`,
          comparison_case_id: `fix-greeting__${comparison}__demo-agent`,
          verdict: 'evidence_limited',
          hard_delta: 0,
          hard_check_delta: null,
          validation_delta: selectedBaseline === 'baseline' ? 1 : -1,
          total_tokens_delta: null,
          summary: '证据不足，需先补齐 validation、hard check 或 telemetry 后再判断。',
          evidence_gaps:
            selectedBaseline === 'baseline'
              ? evidenceGaps('baseline', 'baseline')
              : evidenceGaps('comparison', 'baseline'),
          experiment_variant: comparison,
          experiment_case_id: `fix-greeting__${comparison}__demo-agent`,
        },
      ],
      cases: [baselineCase, experimentCase],
    };
  };

  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url());
    const apiPath = url.pathname;
    if (apiPath === '/api/health') {
      await fulfillJson(route, {
        ok: true,
        initial_config_path: 'context-eval.yaml',
        workspace: { state: 'configured', has_config: true, config_path: 'context-eval.yaml' },
      });
      return;
    }
    if (apiPath === '/api/config/load') {
      await fulfillJson(route, loadedPayload);
      return;
    }
    if (apiPath === '/api/preflight') {
      await fulfillJson(route, { ok: true, checks: ['config_structure', 'repo_path', 'git_ref'] });
      return;
    }
    if (apiPath === '/api/run-plan') {
      await fulfillJson(route, {
        ok: true,
        case_count: 2,
        cleanup_policy: 'successful',
        jobs: 1,
        trials: 1,
        output_dir: './runs',
        agents: ['demo-agent'],
        tasks: ['fix-greeting'],
        variants: ['baseline', 'experiment'],
        cases: [
          {
            case_id: 'fix-greeting__baseline__demo-agent',
            agent_name: 'demo-agent',
            agent_kind: 'custom',
            task_id: 'fix-greeting',
            variant: 'baseline',
            trial_index: 1,
            repo_ref: 'main',
            command_preview: 'python scripts/example_agent.py prompt',
            expected_outcome_summary: 'Greeting is fixed.',
            hard_evaluation_enabled: true,
            soft_evaluation_enabled: true,
          },
          {
            case_id: 'fix-greeting__experiment__demo-agent',
            agent_name: 'demo-agent',
            agent_kind: 'custom',
            task_id: 'fix-greeting',
            variant: 'experiment',
            trial_index: 1,
            repo_ref: 'main',
            command_preview: 'python scripts/example_agent.py prompt',
            expected_outcome_summary: 'Greeting is fixed.',
            hard_evaluation_enabled: true,
            soft_evaluation_enabled: true,
          },
        ],
      });
      return;
    }
    if (apiPath === '/api/runs') {
      await fulfillJson(route, {
        ok: true,
        app_run_id: 'browser-acceptance',
        status: 'completed',
        run_dir: './runs/browser-acceptance',
        case_count: 2,
        completed_cases: 2,
      });
      return;
    }
    if (apiPath === '/api/runs/browser-acceptance/logs') {
      await fulfillJson(route, { ok: true, console: ['done'], files: [] });
      return;
    }
    if (apiPath === '/api/results') {
      await fulfillJson(route, resultsPayload(url.searchParams.get('baseline_variant') || 'baseline'));
      return;
    }
    if (apiPath === '/api/case-detail') {
      await fulfillJson(route, {
        ok: true,
        run_dir: './runs/browser-acceptance',
        case: baselineCase,
        patch: {
          path: 'patches/fix-greeting__baseline__demo-agent.patch',
          content: 'diff --git a/fixture_app/greetings.py b/fixture_app/greetings.py\n+context-eval\n',
          exists: true,
        },
        prompt: null,
        logs: [{ kind: 'agent_stdout', path: 'logs/stdout.log', content: 'done', exists: true }],
        hard_evaluation: {
          status: 'skipped',
          score: null,
          max_score: null,
          error: 'workspace cleaned before check',
          checks: [
            {
              name: 'fixture_app/greetings.py',
              status: 'skipped',
              message: 'workspace missing and patch evidence was insufficient',
            },
          ],
        },
        soft_evaluation: {
          status: 'payload_generated',
          payload_path: 'artifacts/fix-greeting__baseline__demo-agent/soft_evaluation_payload.json',
          result_path: null,
        },
        manual_review: manualReview,
      });
      return;
    }
    if (apiPath === '/api/manual-review') {
      await fulfillJson(route, { ok: false, error: 'manual review write failed: disk full' }, 500);
      return;
    }
    await fulfillJson(route, { ok: false, error: `unexpected ${apiPath}` }, 404);
  });

  await page.goto('/');
  await page.getByRole('button', { name: '开始运行' }).click();
  await expect(page.getByTestId('run-status')).toContainText('已完成');
  await expect(page.getByText('结果已生成')).toBeVisible();
  await expect(page.getByLabel('评分依据')).toContainText('Validation confidence');
  await expect(page.getByLabel('评分依据')).toContainText('通过检查数 / 可评分检查数');
  await expect(page.getByLabel('评分依据')).toContainText('payload-only');
  await expect(page.getByLabel('比较基线')).toHaveValue('baseline');
  await expect(page.getByLabel('对比摘要')).toContainText('比较基线没有 validation commands');

  await page.getByLabel('比较基线').selectOption('experiment');
  await expect(page.getByLabel('比较基线')).toHaveValue('experiment');
  await expect(page.getByLabel('对比摘要')).toContainText('对比对象没有 validation commands');

  await page.getByLabel('比较基线').selectOption('baseline');
  const baselineRow = page.locator('tbody tr', { hasText: 'baseline' }).first();
  await baselineRow.getByRole('button', { name: '查看详情' }).click();
  await expect(page.getByRole('heading', { name: '为什么不能高置信判断' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '硬性检查明细' })).toBeVisible();
  await expect(page.getByText('workspace missing and patch evidence was insufficient')).toBeVisible();
  await expect(page.getByLabel('软性复核材料')).toContainText('payload-only');

  await page.getByLabel('复核人').fill('manual');
  await page.getByRole('button', { name: '保存复核' }).click();
  await expect(page.getByText('错误: manual review write failed: disk full')).toBeVisible();

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  );
  expect(hasHorizontalOverflow).toBe(false);
  await page.screenshot({
    path: path.join(frontendDir, 'test-results', `scoring-baseline-${testInfo.project.name}.png`),
    fullPage: true,
  });
});

test('can request stop for a running local run', async ({ page }) => {
  let runStatus = 'running';
  const loadedPayload = {
    ok: true,
    config_path: 'context-eval.yaml',
    tasks_path: 'tasks.yaml',
    config_yaml: 'repo:\n  path: ./demo-repo\n',
    tasks_yaml: 'tasks:\n  - id: stop-demo\n    prompt: Stop demo.\n',
    editable: {
      repo: { path: './demo-repo', base_ref: 'main' },
      agent: {
        name: 'demo-agent',
        kind: 'custom',
        command: 'python scripts/example_agent.py "{prompt_file}"',
        timeout_minutes: 2,
        network: 'disabled',
      },
      agent_shape: 'agent',
      agents: [
        {
          name: 'demo-agent',
          kind: 'custom',
          command: 'python scripts/example_agent.py "{prompt_file}"',
          timeout_minutes: 2,
          network: 'disabled',
        },
      ],
      tasks_path: './tasks.yaml',
      variants: [{ name: 'baseline', description: 'Baseline', overlays: [] }],
      tasks: [
        {
          id: 'stop-demo',
          title: 'Stop demo',
          prompt: 'Keep running until stopped.',
          category: 'runtime',
          difficulty: 'easy',
          validation_commands: [],
          expected_outcome: { summary: 'Run can be stopped.', acceptance_points: [] },
          hard_evaluation: {
            enabled: false,
            require_validation_pass: false,
            required_paths: [],
            forbidden_paths: [],
            expected_snippets: [],
            forbidden_snippets: [],
          },
          soft_evaluation: { enabled: false, mode: 'payload-only', max_score: 10, rubric: [] },
        },
      ],
      evaluation_commands: [],
      evaluation_timeout_seconds: null,
      output_dir: './runs',
    },
    resolved: {
      repo_path: './demo-repo',
      output_dir: './runs',
      agents: ['demo-agent'],
      variants: ['baseline'],
      tasks: ['stop-demo'],
    },
  };

  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url());
    const apiPath = url.pathname;
    if (apiPath === '/api/health') {
      await fulfillJson(route, {
        ok: true,
        initial_config_path: 'context-eval.yaml',
        workspace: { state: 'configured', has_config: true, config_path: 'context-eval.yaml' },
      });
      return;
    }
    if (apiPath === '/api/config/load') {
      await fulfillJson(route, loadedPayload);
      return;
    }
    if (apiPath === '/api/preflight') {
      await fulfillJson(route, { ok: true, checks: ['config_structure', 'repo_path', 'git_ref'] });
      return;
    }
    if (apiPath === '/api/run-plan') {
      await fulfillJson(route, {
        ok: true,
        case_count: 1,
        cleanup_policy: 'successful',
        jobs: 1,
        trials: 1,
        output_dir: './runs',
        agents: ['demo-agent'],
        tasks: ['stop-demo'],
        variants: ['baseline'],
        cases: [
          {
            case_id: 'stop-demo__baseline__demo-agent',
            agent_name: 'demo-agent',
            agent_kind: 'custom',
            task_id: 'stop-demo',
            variant: 'baseline',
            trial_index: 1,
            repo_ref: 'main',
            command_preview: 'python scripts/example_agent.py prompt',
            expected_outcome_summary: 'Run can be stopped.',
            hard_evaluation_enabled: false,
            soft_evaluation_enabled: false,
          },
        ],
      });
      return;
    }
    if (apiPath === '/api/runs' && route.request().method() === 'POST') {
      runStatus = 'running';
      await fulfillJson(route, {
        ok: true,
        app_run_id: 'stop-demo',
        status: runStatus,
        run_dir: './runs/stop-demo',
        case_count: 1,
        completed_cases: 0,
      });
      return;
    }
    if (apiPath === '/api/runs/stop-demo') {
      await fulfillJson(route, {
        ok: true,
        app_run_id: 'stop-demo',
        status: runStatus,
        run_dir: './runs/stop-demo',
        case_count: 1,
        completed_cases: 0,
      });
      return;
    }
    if (apiPath === '/api/runs/stop-demo/logs') {
      await fulfillJson(route, { ok: true, console: ['running stop demo'], files: [] });
      return;
    }
    if (apiPath === '/api/runs/stop-demo/stop') {
      runStatus = 'stop_requested';
      await fulfillJson(route, { ok: true, status: runStatus });
      return;
    }
    await fulfillJson(route, { ok: false, error: `unexpected ${apiPath}` }, 404);
  });

  await page.goto('/');
  const runButtons = page.locator('.run-brief-panel .button-row button');
  await runButtons.nth(1).click();
  await expect(page.getByTestId('run-status')).toContainText('运行中 0/1');
  await expect(runButtons.nth(2)).toBeEnabled();
  await runButtons.nth(2).click();
  await expect(page.getByTestId('run-status')).toContainText('正在停止 0/1');
  await expectNoHorizontalOverflow(page);
  await expectNoVerticalButtonText(page);
});

test('completes the local server workflow with fake Coco and hybrid evaluation', async ({ page }) => {
  test.setTimeout(90_000);
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'context-eval-app-'));
  const fixture = copyFixtureRepo(workspace);
  writeWorkflowFiles(workspace, fixture);
  const server = await startLocalApp(workspace);

  try {
    await page.goto(server.url);

    await expect(page.getByRole('heading', { name: 'context-eval 本地工作台' })).toBeVisible();
    await page.getByText('配置与任务细节').click();
    await page.getByRole('button', { name: '加载配置' }).click();
    await expect(page.getByLabel('仓库路径')).toHaveValue(toPosix(fixture));
    await expect(
      page.locator('.status-line', { hasText: 'Greeting uses context-eval wording.' }),
    ).toBeVisible();

    await page.getByRole('button', { name: '开始运行' }).click();
    await expect(page.getByTestId('preflight-status')).toContainText('运行前检查通过');
    await expect(page.getByTestId('planned-case-count')).toHaveText('2');
    await expect(page.getByTestId('run-status')).toContainText('已完成', { timeout: 60000 });
    await expect(page.getByText('结果已生成')).toBeVisible();

    await expect(page.getByLabel('评分依据')).toContainText('Validation confidence');
    await expect(page.getByLabel('评分依据')).toContainText('通过检查数 / 可评分检查数');
    const baselineRow = page.locator('tbody tr', { hasText: 'baseline' }).first();
    await expect(baselineRow).toContainText('通过 3/3');
    await expect(baselineRow).toContainText('通过检查数 / 可评分检查数');
    await expect(baselineRow).toContainText('已生成待复核材料');
    await expect(page.getByLabel('比较基线')).toHaveValue('baseline');
    await expect(page.getByLabel('对比摘要')).toContainText('对比对象');
    await page.getByLabel('比较基线').selectOption('experiment');
    await expect(page.getByLabel('比较基线')).toHaveValue('experiment');
    await expect(page.getByLabel('对比摘要')).toContainText('baseline');

    await baselineRow.getByRole('button', { name: '查看详情' }).click();
    await expect(page.getByRole('heading', { name: '硬性检查明细' })).toBeVisible();
    await expect(page.getByLabel('软性复核材料')).toContainText('payload-only');

    await page.getByRole('button', { name: '导出 JSON' }).click();
    await expect(page.getByTestId('export-output')).toContainText('"case_count": 2');
    await page.getByRole('button', { name: '导出 CSV' }).click();
    await expect(page.getByTestId('export-output')).toContainText('case_id');
    await page.getByRole('button', { name: '导出 Markdown' }).click();
    await expect(page.getByTestId('export-output')).toContainText('context-eval evaluates');
    await page.getByRole('button', { name: '导出 HTML' }).click();
    await expect(page.getByTestId('export-output')).toContainText('context-eval local UI');
    await expectNoHorizontalOverflow(page);
    await expectNoVerticalButtonText(page);
  } finally {
    await stopLocalApp(server.child);
    fs.rmSync(workspace, { recursive: true, force: true });
  }
});
