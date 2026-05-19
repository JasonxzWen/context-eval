import { localAppFixture } from './fixture';
import type { EditableAgent, EditableConfig, EditableTask, EditableVariant, LoadedConfig } from './types';

export function fallbackConfig(): LoadedConfig {
  const fallbackAgents: EditableAgent[] = localAppFixture.agents.map((agent) => ({
    name: agent.name,
    kind: agent.kind,
    command: agent.command,
    timeout_minutes: 60,
    network: 'disabled',
  }));
  const fallbackTasks: EditableTask[] = localAppFixture.tasks.map((task) => ({
    id: task,
    title: task,
    prompt: `Run ${task}.`,
    validation_commands: [],
    expected_outcome: {
      summary: '示例任务会生成本地补丁证据。',
      acceptance_points: ['本地结果可审查。'],
    },
    hard_evaluation: {
      enabled: true,
      require_validation_pass: false,
      required_paths: ['README.md'],
      forbidden_paths: [],
      expected_snippets: [],
      forbidden_snippets: [],
      command_checks: [],
    },
    soft_evaluation: {
      enabled: true,
      mode: 'payload-only',
      max_score: 10,
      rubric: [{ name: 'quality', weight: 1, description: 'Patch is clear.' }],
    },
  }));
  const fallbackVariants: EditableVariant[] = localAppFixture.variants.map((variant) => ({
    name: variant,
    description: variant,
    overlays: [],
  }));
  const configYaml = [
    'repo:',
    '  path: ./fixture-repo',
    '  base_ref: main',
    'agents:',
    ...fallbackAgents.flatMap((agent) => [
      `  ${agent.name}:`,
      `    kind: ${agent.kind}`,
      `    command: ${JSON.stringify(agent.command)}`,
      '    timeout_minutes: 60',
      '    network: disabled',
    ]),
    'tasks: ./tasks.yaml',
    'output_dir: ./runs',
    'variants:',
    ...fallbackVariants.flatMap((variant) => [
      `  ${variant.name}:`,
      `    description: ${variant.description}`,
      '    overlays: []',
    ]),
    'evaluation:',
    '  commands: []',
    '',
  ].join('\n');
  const tasksYaml = [
    'tasks:',
    ...fallbackTasks.flatMap((task) => [
      `  - id: ${task.id}`,
      `    title: ${task.title}`,
      `    prompt: ${task.prompt}`,
      '    expected_outcome:',
      `      summary: ${task.expected_outcome?.summary}`,
      '    hard_evaluation:',
      '      enabled: true',
      '      required_paths: [README.md]',
      '    soft_evaluation:',
      '      enabled: true',
      '      mode: payload-only',
    ]),
    '',
  ].join('\n');
  return {
    config_path: 'context-eval.yaml',
    tasks_path: 'tasks.yaml',
    config_yaml: configYaml,
    tasks_yaml: tasksYaml,
    editable: {
      repo: { path: './fixture-repo', base_ref: 'main' },
      agent: fallbackAgents[0],
      agent_shape: 'agents',
      agents: fallbackAgents,
      tasks_path: './tasks.yaml',
      variants: fallbackVariants,
      tasks: fallbackTasks,
      evaluation_commands: [],
      output_dir: './runs',
    },
    resolved: {
      repo_path: './fixture-repo',
      output_dir: './runs',
      agents: fallbackAgents.map((agent) => agent.name),
      variants: fallbackVariants.map((variant) => variant.name),
      tasks: fallbackTasks.map((task) => task.id),
    },
  };
}

export function emptyConfig(): LoadedConfig {
  return {
    config_path: 'context-eval.yaml',
    tasks_path: 'tasks.yaml',
    config_yaml: '',
    tasks_yaml: '',
    editable: emptyEditableConfig(),
    resolved: {
      repo_path: '',
      output_dir: './runs',
      agents: [],
      variants: [],
      tasks: [],
    },
  };
}

function emptyEditableConfig(): EditableConfig {
  return {
    repo: { path: '', base_ref: 'main' },
    agent: {
      name: '',
      kind: 'custom',
      command: '',
      timeout_minutes: 60,
      network: 'disabled',
    },
    agent_shape: 'agent',
    agents: [],
    tasks_path: './tasks.yaml',
    variants: [],
    tasks: [],
    evaluation_commands: [],
    output_dir: './runs',
  };
}

export function agentsFrom(loaded: LoadedConfig) {
  return loaded.editable.agent_shape === 'agents'
    ? loaded.editable.agents
    : [loaded.editable.agent];
}

export function primaryAgent(loaded: LoadedConfig) {
  return agentsFrom(loaded).find((agent) => agent.kind === 'coco') || agentsFrom(loaded)[0];
}

export function listText(values: string[] | undefined, fallback = '未配置') {
  return values && values.length > 0 ? values.join(', ') : fallback;
}
