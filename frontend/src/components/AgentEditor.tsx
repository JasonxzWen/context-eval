import type { EditableAgent } from '../types';

type AgentEditorProps = {
  agents: EditableAgent[];
  selectedAgentIndex: number;
  saveStatus: string;
  serverMode: 'checking' | 'connected' | 'fixture';
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

function agentKindLabel(value: string) {
  return agentKinds.find((kind) => kind.value === value)?.label || value;
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
  return {
    name: uniqueAgentName('new-agent', agents),
    kind: 'custom',
    command: '',
    timeout_minutes: 60,
    network: 'disabled',
  };
}

export function AgentEditor({
  agents,
  selectedAgentIndex,
  saveStatus,
  serverMode,
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
    if (!window.confirm(`删除执行器 "${agent.name}"？`)) return;
    onUpdateAgents(agents.filter((_, index) => index !== selectedIndex));
    onSelectAgent(Math.max(0, selectedIndex - 1));
  }

  return (
    <section className="panel agent-editor-panel" aria-label="执行器配置">
      <div className="panel-heading">
        <h2>执行器配置</h2>
        <span>{agents.length}</span>
      </div>
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
                配置名称
                <input
                  id="agent-name"
                  aria-label="执行器名称"
                  value={agent.name}
                  onChange={(event) => updateAgent({ name: event.target.value })}
                />
              </label>
              <label htmlFor="agent-kind">
                类型
                <select
                  id="agent-kind"
                  aria-label="执行器类型"
                  value={agent.kind}
                  onChange={(event) => updateAgent({ kind: event.target.value })}
                >
                  {agentKinds.map((kind) => (
                    <option value={kind.value} key={kind.value}>
                      {kind.label}
                    </option>
                  ))}
                </select>
              </label>
              <label htmlFor="agent-timeout">
                超时（分钟）
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
                联网权限
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
            <label htmlFor="agent-command">
              命令模板
              <textarea
                id="agent-command"
                aria-label="执行器命令模板"
                value={agent.command}
                onChange={(event) => updateAgent({ command: event.target.value })}
                spellCheck={false}
              />
            </label>
            <div className="button-row editor-actions">
              <button type="submit" disabled={serverMode !== 'connected'}>
                保存执行器配置
              </button>
              <span className="status-line" data-testid="agent-save-status">
                {saveStatus}
              </span>
            </div>
          </form>
        </div>
      ) : (
        <div className="empty-editor">
          <p className="status-line">当前配置没有执行器。</p>
          <button type="button" onClick={addAgent}>
            新建执行器
          </button>
        </div>
      )}
    </section>
  );
}
