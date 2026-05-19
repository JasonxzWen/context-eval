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
            <strong>试用示例</strong>
            <p>创建一个本地演示仓库、两组上下文版本、一个假执行器和可对比的硬性检查结果。</p>
          </div>
          <button type="button" onClick={onBootstrapDemo}>
            试用示例
          </button>
        </article>
        <article className="setup-option">
          <div>
            <strong>打开真实项目</strong>
            <p>从已有 Git 仓库生成评测工作区，然后继续配置执行器、上下文版本和任务。</p>
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
