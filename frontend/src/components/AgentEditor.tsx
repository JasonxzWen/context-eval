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

const agentKinds = ['custom', 'coco', 'codex-cli', 'claude-code', 'traecli'];

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
    if (!window.confirm(`删除 agent "${agent.name}"？`)) return;
    onUpdateAgents(agents.filter((_, index) => index !== selectedIndex));
    onSelectAgent(Math.max(0, selectedIndex - 1));
  }

  return (
    <section className="panel agent-editor-panel" aria-label="Agent profiles">
      <div className="panel-heading">
        <h2>Agent Profiles</h2>
        <span>{agents.length}</span>
      </div>
      {agent ? (
        <div className="editor-split">
          <aside className="task-rail" aria-label="agent 列表">
            {agents.map((item, index) => (
              <button
                type="button"
                className={index === selectedIndex ? 'task-tab active' : 'task-tab'}
                key={`${item.name}:${index}`}
                aria-label={`选择 agent ${item.name || index + 1}`}
                onClick={() => onSelectAgent(index)}
              >
                <strong>{item.name || `agent-${index + 1}`}</strong>
                <span>{item.kind || 'custom'}</span>
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
                profile name
                <input
                  id="agent-name"
                  aria-label="agent name"
                  value={agent.name}
                  onChange={(event) => updateAgent({ name: event.target.value })}
                />
              </label>
              <label htmlFor="agent-kind">
                kind
                <select
                  id="agent-kind"
                  aria-label="agent kind"
                  value={agent.kind}
                  onChange={(event) => updateAgent({ kind: event.target.value })}
                >
                  {agentKinds.map((kind) => (
                    <option value={kind} key={kind}>
                      {kind}
                    </option>
                  ))}
                </select>
              </label>
              <label htmlFor="agent-timeout">
                timeout minutes
                <input
                  id="agent-timeout"
                  aria-label="agent timeout minutes"
                  type="number"
                  min="1"
                  value={agent.timeout_minutes}
                  onChange={(event) => updateAgent({ timeout_minutes: Number(event.target.value) })}
                />
              </label>
              <label htmlFor="agent-network">
                network
                <select
                  id="agent-network"
                  aria-label="agent network"
                  value={agent.network}
                  onChange={(event) => updateAgent({ network: event.target.value })}
                >
                  <option value="disabled">disabled</option>
                  <option value="enabled">enabled</option>
                </select>
              </label>
            </div>
            <label htmlFor="agent-command">
              command
              <textarea
                id="agent-command"
                aria-label="agent command"
                value={agent.command}
                onChange={(event) => updateAgent({ command: event.target.value })}
                spellCheck={false}
              />
            </label>
            <div className="button-row editor-actions">
              <button type="submit" disabled={serverMode !== 'connected'}>
                保存 agent 配置
              </button>
              <span className="status-line" data-testid="agent-save-status">
                {saveStatus}
              </span>
            </div>
          </form>
        </div>
      ) : (
        <div className="empty-editor">
          <p className="status-line">当前配置没有 agent profile。</p>
          <button type="button" onClick={addAgent}>
            新建 agent
          </button>
        </div>
      )}
    </section>
  );
}
