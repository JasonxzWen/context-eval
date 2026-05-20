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
    const label = `第 ${index + 1} 个上下文方案`;
    if (!variant.name.trim()) {
      issues.push(`${label}名称不能为空`);
    }
    variant.overlays.forEach((overlay, overlayIndex) => {
      const overlayLabel = `${label}的第 ${overlayIndex + 1} 个上下文资料`;
      if (!overlay.source.trim()) {
        issues.push(`${overlayLabel}来源路径不能为空`);
      }
      if (!overlay.target.trim()) {
        issues.push(`${overlayLabel}目标路径不能为空`);
      }
    });
  });
  duplicateVariants.forEach((name) => issues.push(`上下文方案名称重复: ${name}`));

  const agentProfiles =
    editable.agent_shape === 'agents'
      ? (editable.agents.length > 0 ? editable.agents : [editable.agent])
      : [editable.agent];
  const agentNames = agentProfiles.map((agent) => agent.name.trim());
  const duplicateAgents = [
    ...new Set(agentNames.filter((name, index) => name && agentNames.indexOf(name) !== index)),
  ];
  agentProfiles.forEach((agent, index) => {
    const label = `第 ${index + 1} 个执行器`;
    if (!agent.name.trim()) {
      issues.push(`${label}名称不能为空`);
    }
    if (!agent.command.trim()) {
      issues.push(`${label}命令模板不能为空`);
    }
    if (!(agent.timeout_minutes > 0)) {
      issues.push(`${label}超时必须大于 0`);
    }
    if (!['disabled', 'enabled'].includes(agent.network)) {
      issues.push(`${label}联网权限必须是“禁止联网”或“允许联网”`);
    }
  });
  duplicateAgents.forEach((name) => issues.push(`执行器名称重复: ${name}`));

  const ids = editable.tasks.map((task) => task.id.trim());
  const duplicates = [...new Set(ids.filter((id, index) => id && ids.indexOf(id) !== index))];
  editable.tasks.forEach((task, index) => {
    const label = task.id.trim() || `第 ${index + 1} 个测试用例`;
    if (!task.id.trim()) {
      issues.push(`${label}: 任务 ID 不能为空`);
    }
    if (!task.prompt.trim()) {
      issues.push(`${label}: 任务说明不能为空`);
    }
    task.validation_commands.forEach((command, commandIndex) => {
      if (!command.trim()) {
        issues.push(`${label}: 第 ${commandIndex + 1} 条验证命令不能为空`);
      }
    });
    task.hard_evaluation?.command_checks?.forEach((check, checkIndex) => {
      if (!check.label.trim()) {
        issues.push(`${label}: 第 ${checkIndex + 1} 条命令检查名称不能为空`);
      }
      if (!check.command.trim()) {
        issues.push(`${label}: 第 ${checkIndex + 1} 条命令检查内容不能为空`);
      }
    });
    task.soft_evaluation?.rubric?.forEach((item, rubricIndex) => {
      if (!item.name.trim()) {
        issues.push(`${label}: 第 ${rubricIndex + 1} 条评分规则名称不能为空`);
      }
      if (!(item.weight > 0)) {
        issues.push(`${label}: 第 ${rubricIndex + 1} 条评分规则权重必须大于 0`);
      }
    });
  });
  duplicates.forEach((id) => issues.push(`任务 ID 重复: ${id}`));
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
    title: '新的测试用例',
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
