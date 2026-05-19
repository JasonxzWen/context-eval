import { localAppFixture } from './fixture';
import type {
  EditableAgent,
  EditableConfig,
  EditableTask,
  EditableVariant,
  LoadedConfig,
  RunScope,
} from './types';

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

export function validateEditableConfig(editable: EditableConfig) {
  const issues: string[] = [];
  const variantNames = editable.variants.map((variant) => variant.name.trim());
  const duplicateVariants = [
    ...new Set(variantNames.filter((name, index) => name && variantNames.indexOf(name) !== index)),
  ];
  editable.variants.forEach((variant, index) => {
    const label = `variant ${index + 1}`;
    if (!variant.name.trim()) {
      issues.push(`${label} name 不能为空`);
    }
    variant.overlays.forEach((overlay, overlayIndex) => {
      const overlayLabel = `${label} overlay ${overlayIndex + 1}`;
      if (!overlay.source.trim()) {
        issues.push(`${overlayLabel} source 不能为空`);
      }
      if (!overlay.target.trim()) {
        issues.push(`${overlayLabel} target 不能为空`);
      }
    });
  });
  duplicateVariants.forEach((name) => issues.push(`重复 variant name: ${name}`));

  const agentProfiles =
    editable.agent_shape === 'agents'
      ? (editable.agents.length > 0 ? editable.agents : [editable.agent])
      : [editable.agent];
  const agentNames = agentProfiles.map((agent) => agent.name.trim());
  const duplicateAgents = [
    ...new Set(agentNames.filter((name, index) => name && agentNames.indexOf(name) !== index)),
  ];
  agentProfiles.forEach((agent, index) => {
    const label = `agent profile ${index + 1}`;
    if (!agent.name.trim()) {
      issues.push(`${label} name 不能为空`);
    }
    if (!agent.command.trim()) {
      issues.push(`${label} command 不能为空`);
    }
    if (!(agent.timeout_minutes > 0)) {
      issues.push(`${label} timeout 必须大于 0`);
    }
    if (!['disabled', 'enabled'].includes(agent.network)) {
      issues.push(`${label} network 必须是 disabled 或 enabled`);
    }
  });
  duplicateAgents.forEach((name) => issues.push(`重复 agent profile name: ${name}`));

  const ids = editable.tasks.map((task) => task.id.trim());
  const duplicates = [...new Set(ids.filter((id, index) => id && ids.indexOf(id) !== index))];
  editable.tasks.forEach((task, index) => {
    const label = task.id.trim() || `第 ${index + 1} 个 task`;
    if (!task.id.trim()) {
      issues.push(`${label}: task id 不能为空`);
    }
    if (!task.prompt.trim()) {
      issues.push(`${label}: prompt 不能为空`);
    }
    task.validation_commands.forEach((command, commandIndex) => {
      if (!command.trim()) {
        issues.push(`${label}: validation command ${commandIndex + 1} 不能为空`);
      }
    });
    task.hard_evaluation?.command_checks?.forEach((check, checkIndex) => {
      if (!check.label.trim()) {
        issues.push(`${label}: command check ${checkIndex + 1} label 不能为空`);
      }
      if (!check.command.trim()) {
        issues.push(`${label}: command check ${checkIndex + 1} command 不能为空`);
      }
    });
    task.soft_evaluation?.rubric?.forEach((item, rubricIndex) => {
      if (!item.name.trim()) {
        issues.push(`${label}: rubric ${rubricIndex + 1} name 不能为空`);
      }
      if (!(item.weight > 0)) {
        issues.push(`${label}: rubric ${rubricIndex + 1} weight 必须大于 0`);
      }
    });
  });
  duplicates.forEach((id) => issues.push(`重复 task id: ${id}`));
  return issues;
}

export function uniqueTaskId(base: string, tasks: EditableTask[]) {
  const used = new Set(tasks.map((task) => task.id));
  if (!used.has(base)) return base;
  let suffix = 2;
  while (used.has(`${base}-${suffix}`)) {
    suffix += 1;
  }
  return `${base}-${suffix}`;
}

export function blankTask(tasks: EditableTask[]): EditableTask {
  return {
    id: uniqueTaskId('new-task', tasks),
    title: 'New evaluation task',
    prompt: '',
    category: 'bugfix',
    difficulty: 'easy',
    validation_commands: [],
    expected_outcome: {
      summary: '',
      acceptance_points: [],
      files: [],
    },
    hard_evaluation: {
      enabled: true,
      require_validation_pass: false,
      required_paths: [],
      forbidden_paths: [],
      expected_snippets: [],
      forbidden_snippets: [],
      command_checks: [],
    },
    soft_evaluation: {
      enabled: true,
      mode: 'payload-only',
      max_score: 10,
      rubric: [],
    },
  };
}

export function emptyRunScope(): RunScope {
  return { task_ids: [], variants: [], agents: [] };
}

export function availableScope(payload: LoadedConfig): RunScope {
  return {
    task_ids: payload.editable.tasks.map((task) => task.id).filter(Boolean),
    variants: payload.editable.variants.map((variant) => variant.name).filter(Boolean),
    agents: agentsFrom(payload).map((agent) => agent.name).filter(Boolean),
  };
}

function selectedEverything(selected: string[], available: string[]) {
  return available.length > 0 && available.every((value) => selected.includes(value));
}

export function reconcileRunScope(
  current: RunScope,
  previousAvailable: RunScope,
  nextAvailable: RunScope,
  initialized: boolean,
) {
  if (!initialized) {
    return { scope: nextAvailable, changed: false };
  }

  function reconcileDimension(
    selected: string[],
    previous: string[],
    next: string[],
  ) {
    if (selectedEverything(selected, previous)) {
      return {
        values: next,
        changed: selected.length !== next.length || next.some((value) => !selected.includes(value)),
      };
    }
    const filtered = selected.filter((value) => next.includes(value));
    if (filtered.length === 0 && next.length > 0) {
      return { values: next, changed: selected.length > 0 };
    }
    return { values: filtered, changed: filtered.length !== selected.length };
  }

  const taskScope = reconcileDimension(
    current.task_ids,
    previousAvailable.task_ids,
    nextAvailable.task_ids,
  );
  const variantScope = reconcileDimension(
    current.variants,
    previousAvailable.variants,
    nextAvailable.variants,
  );
  const agentScope = reconcileDimension(
    current.agents,
    previousAvailable.agents,
    nextAvailable.agents,
  );
  return {
    scope: {
      task_ids: taskScope.values,
      variants: variantScope.values,
      agents: agentScope.values,
    },
    changed: taskScope.changed || variantScope.changed || agentScope.changed,
  };
}
