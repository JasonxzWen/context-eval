import { listText } from '../localConfig';
import type { EditableAgent, EditableTask, LoadedConfig } from '../types';

type AdvancedConfigDetailsProps = {
  agents: EditableAgent[];
  configPath: string;
  configYaml: string;
  loaded: LoadedConfig;
  modeLabel: string;
  saveStatus: string;
  serverMode: 'checking' | 'connected' | 'fixture';
  task: EditableTask | undefined;
  tasksYaml: string;
  onConfigPathChange: (value: string) => void;
  onConfigYamlChange: (value: string) => void;
  onLoadConfig: () => void;
  onSaveConfig: () => void;
  onTasksYamlChange: (value: string) => void;
};

export function AdvancedConfigDetails({
  agents,
  configPath,
  configYaml,
  loaded,
  modeLabel,
  saveStatus,
  serverMode,
  task,
  tasksYaml,
  onConfigPathChange,
  onConfigYamlChange,
  onLoadConfig,
  onSaveConfig,
  onTasksYamlChange,
}: AdvancedConfigDetailsProps) {
  const cocoAgent = agents.find((agent) => agent.kind === 'coco') || agents[0];

  return (
    <details className="advanced-workbench">
      <summary>
        <span>配置与任务细节</span>
        <small>Agent、Context、验收标准和 YAML</small>
      </summary>
      <div className="advanced-grid">
        <section className="panel project-panel">
          <div className="panel-heading">
            <h2>Project</h2>
            <span>{modeLabel}</span>
          </div>
          <div className="form-grid">
            <label htmlFor="config-path">
              配置路径
              <input
                id="config-path"
                value={configPath}
                onChange={(event) => onConfigPathChange(event.target.value)}
              />
            </label>
            <label htmlFor="repo-path">
              仓库路径
              <input id="repo-path" value={loaded.editable.repo.path} readOnly />
            </label>
            <label htmlFor="base-ref">
              base ref
              <input id="base-ref" value={loaded.editable.repo.base_ref} readOnly />
            </label>
            <label htmlFor="output-dir">
              输出目录
              <input id="output-dir" value={loaded.editable.output_dir || './runs'} readOnly />
            </label>
          </div>
          <div className="button-row">
            <button type="button" onClick={onLoadConfig}>
              加载配置
            </button>
            <button type="button" onClick={onSaveConfig} disabled={serverMode !== 'connected'}>
              保存并重载
            </button>
          </div>
          <p className="status-line" data-testid="save-status">
            {saveStatus}
          </p>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Agent</h2>
            <span>{cocoAgent?.kind || 'unknown'}</span>
          </div>
          <ul className="profile-list">
            {agents.map((profile) => (
              <li key={profile.name}>
                <div>
                  <strong>{profile.name}</strong>
                  <span>{profile.kind}</span>
                </div>
                <code>{profile.command}</code>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Context Variants</h2>
          </div>
          <ul className="two-column-list single-list">
            {loaded.editable.variants.map((variant) => (
              <li key={variant.name}>
                <strong>{variant.name}</strong>
                <span>{variant.description || '未描述'}</span>
                <small>{variant.overlays.length} overlay(s)</small>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Tasks</h2>
            <span>{loaded.editable.tasks.length}</span>
          </div>
          <ul className="two-column-list single-list">
            {loaded.editable.tasks.map((item) => (
              <li key={item.id}>
                <strong>{item.id}</strong>
                <span>{item.title || item.prompt}</span>
                <small>{[item.category, item.difficulty].filter(Boolean).join(' / ')}</small>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Expected Outcome</h2>
          </div>
          <p className="status-line">{task?.expected_outcome?.summary || '未配置 summary'}</p>
          <ul className="check-list">
            {(task?.expected_outcome?.acceptance_points || []).map((point) => (
              <li key={point}>{point}</li>
            ))}
            {task?.expected_outcome?.files?.map((file) => (
              <li key={file.path}>
                <strong>{file.path}</strong>
                <span>{file.must_change ? 'must_change' : file.change_type || 'expected'}</span>
              </li>
            ))}
            {(!task?.expected_outcome?.acceptance_points?.length
              && !task?.expected_outcome?.files?.length) && <li>未配置 acceptance_points 或 files</li>}
          </ul>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Hard Evaluation</h2>
            <span>{task?.hard_evaluation?.enabled ? 'enabled' : 'disabled'}</span>
          </div>
          <dl className="compact-list">
            <div>
              <dt>require_validation_pass</dt>
              <dd>{String(Boolean(task?.hard_evaluation?.require_validation_pass))}</dd>
            </div>
            <div>
              <dt>required_paths</dt>
              <dd>{listText(task?.hard_evaluation?.required_paths)}</dd>
            </div>
            <div>
              <dt>forbidden_paths</dt>
              <dd>{listText(task?.hard_evaluation?.forbidden_paths)}</dd>
            </div>
          </dl>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Soft Evaluation</h2>
            <span>{task?.soft_evaluation?.mode || 'not_configured'}</span>
          </div>
          <ul className="check-list">
            {(task?.soft_evaluation?.rubric || []).map((rubric) => (
              <li key={rubric.name}>
                <strong>{rubric.name}</strong>
                <span>{rubric.description}</span>
                <small>weight={rubric.weight}</small>
              </li>
            ))}
            {!task?.soft_evaluation?.rubric?.length && <li>未配置 rubric</li>}
          </ul>
        </section>

        <section className="panel yaml-panel">
          <div className="panel-heading">
            <h2>配置文件</h2>
          </div>
          <label htmlFor="config-yaml">
            context-eval.yaml
            <textarea
              id="config-yaml"
              value={configYaml}
              onChange={(event) => onConfigYamlChange(event.target.value)}
              spellCheck={false}
            />
          </label>
          <label htmlFor="tasks-yaml">
            tasks.yaml
            <textarea
              id="tasks-yaml"
              value={tasksYaml}
              onChange={(event) => onTasksYamlChange(event.target.value)}
              spellCheck={false}
            />
          </label>
        </section>
      </div>
    </details>
  );
}
