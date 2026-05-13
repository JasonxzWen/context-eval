import { localAppFixture, plannedCaseCount } from './fixture';
import './styles.css';

const workflowSteps = [
  { label: 'Project', state: 'Ready' },
  { label: 'Profiles', state: 'Ready' },
  { label: 'Preflight', state: 'Pending' },
  { label: 'Run', state: 'Idle' },
  { label: 'Results', state: 'Local' },
];

export function App() {
  const plannedCases = plannedCaseCount(localAppFixture);

  return (
    <main className="app-shell" data-testid="local-app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Local artifacts only</p>
          <h1>Context Eval Local App</h1>
        </div>
        <div className="status-pill" aria-label="Frontend validation shell">
          Validation shell
        </div>
      </header>

      <section className="workflow-band" aria-label="Workflow state">
        {workflowSteps.map((step) => (
          <div className="workflow-step" key={step.label}>
            <span>{step.label}</span>
            <strong>{step.state}</strong>
          </div>
        ))}
      </section>

      <section className="content-grid">
        <div className="panel matrix-panel">
          <div className="panel-heading">
            <h2>Run Matrix</h2>
            <span data-testid="matrix-count">{plannedCases}</span>
          </div>
          <dl className="metric-grid">
            <div>
              <dt>Agents</dt>
              <dd>{localAppFixture.agents.length}</dd>
            </div>
            <div>
              <dt>Tasks</dt>
              <dd>{localAppFixture.tasks.length}</dd>
            </div>
            <div>
              <dt>Variants</dt>
              <dd>{localAppFixture.variants.length}</dd>
            </div>
            <div>
              <dt>Trials</dt>
              <dd>{localAppFixture.trials}</dd>
            </div>
          </dl>
        </div>

        <div className="panel">
          <div className="panel-heading">
            <h2>Agent Profiles</h2>
          </div>
          <ul className="profile-list">
            {localAppFixture.agents.map((profile) => (
              <li key={profile.name}>
                <div>
                  <strong>{profile.name}</strong>
                  <span>{profile.kind}</span>
                </div>
                <code>{profile.command}</code>
              </li>
            ))}
          </ul>
        </div>

        <div className="panel artifacts-panel">
          <div className="panel-heading">
            <h2>Artifacts</h2>
          </div>
          <ul>
            {localAppFixture.artifacts.map((artifact) => (
              <li key={artifact}>{artifact}</li>
            ))}
          </ul>
        </div>
      </section>
    </main>
  );
}
