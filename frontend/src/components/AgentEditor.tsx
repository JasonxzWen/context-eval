import type { EditableAgent } from '../types';

type AgentEditorProps = {
  agents: EditableAgent[];
  selectedAgentIndex: number;
  saveStatus: string;
  serverMode: 'checking' | 'connected' | 'fixture';
  validationErrors: string[];
  onSelectAgent: (index: number) => void;
  onUpdateAgents: (agents: EditableAgent[]) => void;
  onSave: () => void;
};

const agentKinds = [
  { value: 'custom', label: '自定义命令' },
  { value: 'coco', label: 'Coco' },
  { value: 'codex-cli', label: 'Codex CLI' },
  { value: 'claude-code', label: 'Claude Code' },
  { value: 'traecli', label: 'Trae CLI' },
];

const generatedCommandKinds = new Set(['codex-cli', 'claude-code', 'coco', 'traecli']);

function agentKindLabel(value: string) {
  return agentKinds.find((kind) => kind.value === value)?.label || value;
}

function commandTemplateParts(kind: string): { prefix: string; suffix: string } | null {
  if (kind === 'codex-cli') {
    return {
      prefix: 'codex exec --json',
      suffix: ' --output-last-message "{output_dir}/codex-final-message.md" -C "{workspace}" - < "{prompt_file}"',
    };
  }
  if (kind === 'claude-code') {
    return {
      prefix: 'claude -p',
      suffix: ' < "{prompt_file}"',
    };
  }
  if (kind === 'coco') {
    return {
      prefix: 'coco -y',
      suffix: ' -p "{prompt}"',
    };
  }
  if (kind === 'traecli') {
    return {
      prefix: 'traecli',
      suffix: ' -p "{prompt}"',
    };
  }
  return null;
}

function defaultAgentArgs(kind: string) {
  if (kind === 'codex-cli') return '--sandbox workspace-write';
  if (kind === 'claude-code') return '--output-format stream-json';
  if (kind === 'coco') return '--query-timeout 10m --bash-tool-timeout 5m';
  return '';
}

function buildAgentCommand(kind: string, extraArgs: string = defaultAgentArgs(kind)) {
  const parts = commandTemplateParts(kind);
  if (!parts) return '';
  const trimmed = extraArgs.trim();
  return `${parts.prefix}${trimmed ? ` ${trimmed}` : ''}${parts.suffix}`;
}

function defaultAgentTelemetry(kind: string) {
  if (kind === 'codex-cli') {
    return {
      collector: 'codex-jsonl',
      file: 'codex-events.jsonl',
    };
  }
  return {
    collector: 'none',
    file: 'telemetry.json',
  };
}

function agentExtraArgs(agent: EditableAgent) {
  const parts = commandTemplateParts(agent.kind);
  const command = agent.command.trim();
  if (!parts || !command.startsWith(parts.prefix) || !command.endsWith(parts.suffix)) {
    return '';
  }
  return command.slice(parts.prefix.length, command.length - parts.suffix.length).trim();
}

function uniqueAgentName(base: string, agents: EditableAgent[]) {
  const used = new Set(agents.map((agent) => agent.name));
  if (!used.has(base)) return base;
  let suffix = 2;
  while (used.has(`${base}-${suffix}`)) {
    suffix += 1;
  }
  return `${base}-${suffix}`;
}

function blankAgent(agents: EditableAgent[]): EditableAgent {
  const kind = 'codex-cli';
  return {
    name: uniqueAgentName('codex-cli', agents),
    kind,
    command: buildAgentCommand(kind),
    timeout_minutes: 60,
    network: 'disabled',
    telemetry: defaultAgentTelemetry(kind),
  };
}

export function AgentEditor({
  agents,
  selectedAgentIndex,
  saveStatus,
  serverMode,
  validationErrors,
  onSelectAgent,
  onUpdateAgents,
  onSave,
}: AgentEditorProps) {
  const selectedIndex = Math.min(selectedAgentIndex, Math.max(agents.length - 1, 0));
  const agent = agents[selectedIndex];

  function updateAgent(patch: Partial<EditableAgent>) {
    if (!agent) return;
    onUpdateAgents(
      agents.map((item, index) => (index === selectedIndex ? { ...item, ...patch } : item)),
    );
  }

  function updateAgentKind(kind: string) {
    const next: Partial<EditableAgent> = { kind };
    if (generatedCommandKinds.has(kind)) {
      next.command = buildAgentCommand(kind);
    }
    if (kind === 'codex-cli' || agent?.telemetry?.collector === 'codex-jsonl') {
      next.telemetry = defaultAgentTelemetry(kind);
    }
    updateAgent(next);
  }

  function updateGeneratedArgs(extraArgs: string) {
    updateAgent({ command: buildAgentCommand(agent.kind, extraArgs) });
  }

  function addAgent() {
    onUpdateAgents([...agents, blankAgent(agents)]);
    onSelectAgent(agents.length);
  }

  function duplicateAgent() {
    if (!agent) return;
    const duplicate = {
      ...agent,
      name: uniqueAgentName(`${agent.name || 'agent'}-copy`, agents),
    };
    onUpdateAgents([...agents, duplicate]);
    onSelectAgent(agents.length);
  }

  function deleteAgent() {
    if (!agent || agents.length <= 1) return;
    if (!window.confirm(`删除本地 AI 命令 "${agent.name}"？`)) return;
    onUpdateAgents(agents.filter((_, index) => index !== selectedIndex));
    onSelectAgent(Math.max(0, selectedIndex - 1));
  }

  return (
    <section className="panel agent-editor-panel" id="agent-config" aria-label="执行器配置">
      <div className="panel-heading">
        <h2>3 选择本地 AI</h2>
      </div>
      <p className="panel-note">
        执行器就是实际做题的本地 AI 命令。用 Codex CLI 时建议 `codex exec --json`，这样能采集 token、耗时和工具调用。
      </p>
      {agent ? (
        <div className="editor-split">
          <aside className="task-rail" aria-label="执行器列表">
            {agents.map((item, index) => (
              <button
                type="button"
                className={index === selectedIndex ? 'task-tab active' : 'task-tab'}
                key={`${item.name}:${index}`}
                aria-label={`选择执行器 ${item.name || index + 1}`}
                onClick={() => onSelectAgent(index)}
              >
                <strong>{item.name || `agent-${index + 1}`}</strong>
                <span>{agentKindLabel(item.kind || 'custom')}</span>
              </button>
            ))}
            <div className="button-row rail-actions">
              <button type="button" className="secondary" onClick={addAgent}>
                新建
              </button>
              <button type="button" className="secondary" onClick={duplicateAgent}>
                复制
              </button>
              <button
                type="button"
                className="secondary danger-button"
                onClick={deleteAgent}
                disabled={agents.length <= 1}
              >
                删除
              </button>
            </div>
          </aside>
          <form
            className="config-editor-form"
            noValidate
            onSubmit={(event) => {
              event.preventDefault();
              onSave();
            }}
          >
            <div className="form-grid">
              <label htmlFor="agent-name">
                命令名称
                <input
                  id="agent-name"
                  aria-label="执行器名称"
                  placeholder="例如：codex-cli"
                  value={agent.name}
                  onChange={(event) => updateAgent({ name: event.target.value })}
                />
              </label>
              <label htmlFor="agent-kind">
                AI / 命令类型
                <select
                  id="agent-kind"
                  aria-label="执行器类型"
                  value={agent.kind}
                  onChange={(event) => updateAgentKind(event.target.value)}
                >
                  {agentKinds.map((kind) => (
                    <option value={kind.value} key={kind.value}>
                      {kind.label}
                    </option>
                  ))}
                </select>
              </label>
              {generatedCommandKinds.has(agent.kind) && (
                <label htmlFor="agent-extra-args">
                  启动参数（可选）
                  <input
                    id="agent-extra-args"
                    aria-label="启动参数"
                    placeholder="例如：--model gpt-5.1"
                    value={agentExtraArgs(agent)}
                    onChange={(event) => updateGeneratedArgs(event.target.value)}
                  />
                  <small className="inline-help">系统会自动加入工作区路径和题目提示词</small>
                </label>
              )}
              <label htmlFor="agent-timeout">
                最长运行时间（分钟）
                <input
                  id="agent-timeout"
                  aria-label="执行器超时分钟"
                  type="number"
                  min="1"
                  value={agent.timeout_minutes}
                  onChange={(event) => updateAgent({ timeout_minutes: Number(event.target.value) })}
                />
              </label>
              <label htmlFor="agent-network">
                是否允许联网
                <select
                  id="agent-network"
                  aria-label="执行器联网权限"
                  value={agent.network}
                  onChange={(event) => updateAgent({ network: event.target.value })}
                >
                  <option value="disabled">禁止联网</option>
                  <option value="enabled">允许联网</option>
                </select>
              </label>
            </div>
            {generatedCommandKinds.has(agent.kind) ? (
              <details className="advanced-inline">
                <summary>高级：查看自动生成的完整命令</summary>
                <label htmlFor="agent-command-preview" className="advanced-field-grid">
                  完整命令预览
                  <textarea
                    id="agent-command-preview"
                    aria-label="自动生成的完整命令"
                    value={agent.command || buildAgentCommand(agent.kind)}
                    readOnly
                    spellCheck={false}
                  />
                </label>
              </details>
            ) : (
              <details className="advanced-inline">
                <summary>高级：技术命令（不推荐）</summary>
                <p className="panel-note">只给技术用户使用；推荐优先选择 Codex CLI 或 Claude Code。</p>
                <label htmlFor="agent-command" className="advanced-field-grid">
                  完整命令
                  <textarea
                    id="agent-command"
                    aria-label="自定义完整命令"
                    placeholder='例如：agent -p "{prompt_file}"'
                    value={agent.command}
                    onChange={(event) => updateAgent({ command: event.target.value })}
                    spellCheck={false}
                  />
                </label>
              </details>
            )}
            {validationErrors.length > 0 && (
              <div className="notice validation-notice" role="alert">
                {validationErrors.map((issue) => (
                  <div key={issue}>{issue}</div>
                ))}
              </div>
            )}
            <div className="button-row editor-actions">
              <button type="submit" disabled={serverMode !== 'connected'}>
                保存本地 AI 配置
              </button>
              <span className="status-line" data-testid="agent-save-status">
                {saveStatus}
              </span>
            </div>
          </form>
        </div>
      ) : (
        <div className="empty-editor">
          <p className="status-line">当前配置没有本地 AI 命令。</p>
          <button type="button" onClick={addAgent}>
            新建本地 AI 命令
          </button>
        </div>
      )}
    </section>
  );
}
