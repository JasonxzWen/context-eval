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
  fs.mkdirSync(contextDir, { recursive: true });
  fs.writeFileSync(path.join(contextDir, 'AGENTS.md'), '# Browser workflow instructions\n');
  fs.writeFileSync(
    path.join(workspace, 'tasks.yaml'),
    [
      'tasks:',
      '  - id: fix-greeting-punctuation',
      '    title: Fix greeting punctuation',
      '    prompt: Fix the fixture greeting punctuation.',
      '    category: runtime',
      '    difficulty: easy',
      '',
    ].join('\n'),
  );
  fs.writeFileSync(
    path.join(workspace, 'context-eval.yaml'),
    [
      'repo:',
      `  path: "${toPosix(fixture)}"`,
      '  base_ref: main',
      'agent:',
      '  name: browser-fake-agent',
      `  command: '"${toPosix(python)}" scripts/example_agent.py "{prompt_file}"'`,
      '  timeout_minutes: 1',
      '  network: disabled',
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

async function startLocalApp(workspace: string) {
  const child = spawn(
    python,
    [
      '-m',
      'context_eval',
      'app',
      '--workspace',
      workspace,
      '--config',
      'context-eval.yaml',
      '--port',
      '0',
    ],
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

test('renders the fixture-backed local app shell', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Context Eval Local App' })).toBeVisible();
  await expect(page.getByText('Local artifacts only')).toBeVisible();
  await expect(page.getByTestId('matrix-count')).toHaveText('8');
  await expect(page.getByText('traecli', { exact: true })).toBeVisible();

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  );
  expect(hasHorizontalOverflow).toBe(false);
});

test('completes the local server workflow with fixture repo and fake agent', async ({ page }) => {
  test.setTimeout(90_000);
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'context-eval-app-'));
  const fixture = copyFixtureRepo(workspace);
  writeWorkflowFiles(workspace, fixture);
  const server = await startLocalApp(workspace);

  try {
    await page.goto(server.url);

    await expect(page.getByRole('heading', { name: 'Context Eval Local App' })).toBeVisible();
    await page.getByRole('button', { name: 'Load config' }).click();
    await expect(page.getByLabel('Repo path')).toHaveValue(toPosix(fixture));
    await expect(page.locator('.profile-list strong').filter({ hasText: 'browser-fake-agent' })).toBeVisible();

    await page.getByRole('button', { name: 'Save config' }).click();
    await expect(page.getByTestId('save-status')).toContainText('Saved');

    await page.getByRole('button', { name: 'Run preflight' }).click();
    await expect(page.getByTestId('preflight-status')).toContainText('Preflight passed');

    await page.getByRole('button', { name: 'Plan run' }).click();
    await expect(page.getByTestId('planned-case-count')).toHaveText('1');

    await page.getByRole('button', { name: 'Start run' }).click();
    await expect(page.getByTestId('run-status')).toContainText('completed', { timeout: 60000 });

    await expect(page.getByRole('cell', { name: 'fix-greeting-punctuation' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'completed' })).toBeVisible();

    await page.getByRole('button', { name: 'Export JSON' }).click();
    await expect(page.getByTestId('export-output')).toContainText('"case_count": 1');
  } finally {
    await stopLocalApp(server.child);
    fs.rmSync(workspace, { recursive: true, force: true });
  }
});
