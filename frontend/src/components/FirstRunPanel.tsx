import type { EnvironmentPayload } from '../types';

type FirstRunPanelProps = {
  title?: string;
  subtitle?: string;
  showDemo?: boolean;
  projectRepoPath: string;
  projectRepoUrl: string;
  projectCloneDir: string;
  environment: EnvironmentPayload | null;
  environmentStatus: string;
  onProjectRepoPathChange: (value: string) => void;
  onProjectRepoUrlChange: (value: string) => void;
  onProjectCloneDirChange: (value: string) => void;
  onBootstrapDemo: () => void;
  onInitializeProject: () => void;
  onCloneProject: () => void;
  onCheckEnvironment: () => void;
};

function statusLabel(status: string) {
  if (status === 'ok') return '通过';
  if (status === 'warning') return '提醒';
  return '需处理';
}

export function FirstRunPanel({
  title = '打开评测项目',
  subtitle = '先选要评测的代码仓库',
  showDemo = true,
  projectRepoPath,
  projectRepoUrl,
  projectCloneDir,
  environment,
  environmentStatus,
  onProjectRepoPathChange,
  onProjectRepoUrlChange,
  onProjectCloneDirChange,
  onBootstrapDemo,
  onInitializeProject,
  onCloneProject,
  onCheckEnvironment,
}: FirstRunPanelProps) {
  return (
    <section className="first-run-panel" aria-label={title}>
      <div className="panel-heading">
        <h2>{title}</h2>
        <span>{subtitle}</span>
      </div>
      <div className="first-run-grid">
        {showDemo && (
          <article className="setup-option">
            <div>
              <strong>试用示例</strong>
              <p>生成一套本地演示配置，用来快速熟悉页面。</p>
            </div>
            <button type="button" onClick={onBootstrapDemo}>
              试用示例
            </button>
          </article>
        )}

        <article className="setup-option">
          <div>
            <strong>打开本地项目</strong>
            <p>已经 clone 到本机时，填写仓库文件夹路径。</p>
          </div>
          <label htmlFor="project-repo-path">
            本地仓库路径
            <input
              id="project-repo-path"
              value={projectRepoPath}
              onChange={(event) => onProjectRepoPathChange(event.target.value)}
              placeholder="例如：D:\\SeriaServer"
            />
          </label>
          <div className="button-row">
            <button type="button" onClick={onInitializeProject} disabled={!projectRepoPath.trim()}>
              打开并创建配置
            </button>
            <button type="button" className="secondary" onClick={onCheckEnvironment}>
              检查本机
            </button>
          </div>
        </article>

        <article className="setup-option setup-option-wide">
          <div>
            <strong>从 Git URL 克隆</strong>
            <p>适合私有仓库第一次使用；会克隆到当前评测工作区，不保存账号密码。</p>
          </div>
          <div className="form-grid">
            <label htmlFor="project-repo-url">
              Git URL
              <input
                id="project-repo-url"
                value={projectRepoUrl}
                onChange={(event) => onProjectRepoUrlChange(event.target.value)}
                placeholder="例如：https://code.byted.org/oasis/SeriaServer.git"
              />
            </label>
            <label htmlFor="project-clone-dir">
              本地文件夹名
              <input
                id="project-clone-dir"
                value={projectCloneDir}
                onChange={(event) => onProjectCloneDirChange(event.target.value)}
                placeholder="例如：SeriaServer"
              />
            </label>
          </div>
          <button type="button" onClick={onCloneProject} disabled={!projectRepoUrl.trim()}>
            克隆并创建配置
          </button>
        </article>
      </div>

      <section className="environment-panel" aria-label="本机检查">
        <div className="compact-heading">
          <h3>本机检查</h3>
          <span>{environmentStatus || '未检查'}</span>
        </div>
        {environment?.checks?.length ? (
          <ul className="environment-check-list">
            {environment.checks.map((check) => (
              <li className={`environment-check-row ${check.status}`} key={check.id}>
                <strong>{check.label}</strong>
                <span>{statusLabel(check.status)}</span>
                <small>{check.summary}</small>
                {check.detail && <em>{check.detail}</em>}
              </li>
            ))}
          </ul>
        ) : (
          <p className="status-line">点击“检查本机”查看 Git、Codex CLI 和项目仓库状态。</p>
        )}
      </section>
    </section>
  );
}
