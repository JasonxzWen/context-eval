import { expect, test } from '@playwright/test';
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
  const contextDir = path.join(workspace, 'contexts', 'baseline');
  const agentScript = path.join(workspace, 'fake-coco.py');
  fs.mkdirSync(contextDir, { recursive: true });
  fs.writeFileSync(path.join(contextDir, 'AGENTS.md'), '# Browser workflow instructions\n');
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
      'evaluation:',
      `  commands: ['"${toPosix(python)}" -m pytest']`,
      '',
    ].join('\n'),
  );
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

    await page.getByRole('button', { name: '试用 demo' }).click();
    await expect(page.getByLabel('仓库路径')).toHaveValue('./demo-repo');

    await expect(page.locator('.run-brief-panel')).toContainText('baseline vs experiment');
    await expect(page.getByRole('heading', { name: '评测用例编辑器' })).toBeVisible();
    await page.getByLabel('Expected outcome summary').fill('Visual editor saved summary.');
    await page.getByRole('button', { name: '保存任务' }).click();
    await expect(page.getByTestId('task-save-status')).toContainText('已保存任务并刷新 run plan');
    await expect(page.locator('.matrix-panel')).toContainText('Visual editor saved summary.');

    await page.getByRole('button', { name: '开始运行' }).click();
    await expect(page.getByTestId('preflight-status')).toContainText('运行前检查通过');
    await expect(page.getByTestId('planned-case-count')).toHaveText('2');
    await expect(page.getByTestId('run-status')).toContainText('已完成', { timeout: 60000 });
    await expect(page.getByText('结果已生成')).toBeVisible();
    await expect(page.getByRole('cell', { name: 'hard failed 3/4' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'hard passed 4/4' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Compare Summary' })).toBeVisible();
    await expect(page.getByText('experiment_improved')).toBeVisible();

    const experimentRow = page.locator('tbody tr', { hasText: 'experiment' });
    await experimentRow.getByRole('button').click();
    await expect(page.getByRole('heading', { name: 'Case Detail' })).toBeVisible();
    await expect(page.locator('.case-detail-panel')).toContainText('experiment');
    await expect(page.locator('.artifact-pane').first()).toBeVisible();

    await page.getByLabel('review decision').selectOption('pass');
    await page.getByLabel('review confidence').selectOption('high');
    await page.getByLabel('reviewer').fill('manual');
    await page.getByLabel('review notes').fill('Experiment result accepted.');
    await page.locator('.review-form button[type="submit"]').click();
    await expect(page.locator('.review-form .status-line')).toContainText('Review');

    await page.getByRole('button', { name: /JSON/ }).click();
    await expect(page.getByTestId('export-output')).toContainText('"manual_reviews"');
    await expect(page.getByTestId('export-output')).toContainText('"decision": "pass"');
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
  await expect(page.getByRole('heading', { name: 'Agent' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Expected Outcome' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Hard Evaluation' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Soft Evaluation' })).toBeVisible();

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  );
  expect(hasHorizontalOverflow).toBe(false);
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
    await expect(page.getByTestId('planned-case-count')).toHaveText('1');
    await expect(page.getByTestId('run-status')).toContainText('已完成', { timeout: 60000 });
    await expect(page.getByText('结果已生成')).toBeVisible();

    await expect(page.getByText('hard passed')).toBeVisible();
    await expect(page.getByText('soft payload_generated')).toBeVisible();

    await page.getByRole('button', { name: '导出 JSON' }).click();
    await expect(page.getByTestId('export-output')).toContainText('"case_count": 1');
  } finally {
    await stopLocalApp(server.child);
    fs.rmSync(workspace, { recursive: true, force: true });
  }
});
