type FirstRunPanelProps = {
  projectRepoPath: string;
  onProjectRepoPathChange: (value: string) => void;
  onBootstrapDemo: () => void;
  onInitializeProject: () => void;
};

export function FirstRunPanel({
  projectRepoPath,
  onProjectRepoPathChange,
  onBootstrapDemo,
  onInitializeProject,
}: FirstRunPanelProps) {
  return (
    <section className="first-run-panel" aria-label="首次设置">
      <div className="panel-heading">
        <h2>开始使用</h2>
        <span>空工作区</span>
      </div>
      <div className="first-run-grid">
        <article className="setup-option">
          <div>
            <strong>试用 demo</strong>
            <p>创建一个本地 demo repo、两组 context variants、一个 fake agent 和可对比的硬检查结果。</p>
          </div>
          <button type="button" onClick={onBootstrapDemo}>
            试用 demo
          </button>
        </article>
        <article className="setup-option">
          <div>
            <strong>打开真实项目</strong>
            <p>从已有 Git 仓库生成评测工作区，然后继续配置 agent、context 和任务。</p>
          </div>
          <label htmlFor="project-repo-path">
            项目路径
            <input
              id="project-repo-path"
              value={projectRepoPath}
              onChange={(event) => onProjectRepoPathChange(event.target.value)}
              placeholder="D:\\path\\to\\repo"
            />
          </label>
          <button type="button" onClick={onInitializeProject} disabled={!projectRepoPath.trim()}>
            创建工作区
          </button>
        </article>
      </div>
    </section>
  );
}
