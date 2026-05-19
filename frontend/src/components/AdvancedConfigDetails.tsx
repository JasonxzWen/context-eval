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

const categoryLabels: Record<string, string> = {
  bugfix: '缺陷修复',
  feature: '功能',
  runtime: '运行时',
  documentation: '文档',
  refactor: '重构',
  test: '测试',
  gameplay: '玩法',
  sample: '示例',
};

const difficultyLabels: Record<string, string> = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
};

const agentKindLabels: Record<string, string> = {
  custom: '自定义命令',
  coco: 'Coco',
  'codex-cli': 'Codex CLI',
  'claude-code': 'Claude Code',
  traecli: 'Trae CLI',
};

const softModeLabels: Record<string, string> = {
  'payload-only': '仅生成复核材料',
};

function labelFor(labels: Record<string, string>, value: string | null | undefined) {
  return value ? labels[value] || value : '未配置';
}

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
        <small>执行器、上下文、验收标准和 YAML</small>
      </summary>
      <div className="advanced-grid">
        <section className="panel project-panel">
          <div className="panel-heading">
            <h2>项目</h2>
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
              基准分支
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
            <h2>执行器</h2>
            <span>{labelFor(agentKindLabels, cocoAgent?.kind)}</span>
          </div>
          <ul className="profile-list">
            {agents.map((profile) => (
              <li key={profile.name}>
                <div>
                  <strong>{profile.name}</strong>
                  <span>{labelFor(agentKindLabels, profile.kind)}</span>
                </div>
                <code>{profile.command}</code>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>上下文版本</h2>
          </div>
          <ul className="two-column-list single-list">
            {loaded.editable.variants.map((variant) => (
              <li key={variant.name}>
                <strong>{variant.name}</strong>
                <span>{variant.description || '未描述'}</span>
                <small>{variant.overlays.length} 个覆盖文件</small>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>任务</h2>
            <span>{loaded.editable.tasks.length}</span>
          </div>
          <ul className="two-column-list single-list">
            {loaded.editable.tasks.map((item) => (
              <li key={item.id}>
                <strong>{item.id}</strong>
                <span>{item.title || item.prompt}</span>
                <small>
                  {[labelFor(categoryLabels, item.category), labelFor(difficultyLabels, item.difficulty)]
                    .filter((value) => value !== '未配置')
                    .join(' / ')}
                </small>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>期望结果</h2>
          </div>
          <p className="status-line">{task?.expected_outcome?.summary || '未配置摘要'}</p>
          <ul className="check-list">
            {(task?.expected_outcome?.acceptance_points || []).map((point) => (
              <li key={point}>{point}</li>
            ))}
            {task?.expected_outcome?.files?.map((file) => (
              <li key={file.path}>
                <strong>{file.path}</strong>
                <span>{file.must_change ? '必须变更' : file.change_type || '期望存在'}</span>
              </li>
            ))}
            {(!task?.expected_outcome?.acceptance_points?.length
              && !task?.expected_outcome?.files?.length) && <li>未配置验收点或期望文件</li>}
          </ul>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>硬性检查</h2>
            <span>{task?.hard_evaluation?.enabled ? '已启用' : '未启用'}</span>
          </div>
          <dl className="compact-list">
            <div>
              <dt>要求验证通过</dt>
              <dd>{task?.hard_evaluation?.require_validation_pass ? '是' : '否'}</dd>
            </div>
            <div>
              <dt>必须存在路径</dt>
              <dd>{listText(task?.hard_evaluation?.required_paths)}</dd>
            </div>
            <div>
              <dt>禁止出现路径</dt>
              <dd>{listText(task?.hard_evaluation?.forbidden_paths)}</dd>
            </div>
          </dl>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>人工评审规则</h2>
            <span>{labelFor(softModeLabels, task?.soft_evaluation?.mode)}</span>
          </div>
          <ul className="check-list">
            {(task?.soft_evaluation?.rubric || []).map((rubric) => (
              <li key={rubric.name}>
                <strong>{rubric.name}</strong>
                <span>{rubric.description}</span>
                <small>权重={rubric.weight}</small>
              </li>
            ))}
            {!task?.soft_evaluation?.rubric?.length && <li>未配置评分规则</li>}
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
