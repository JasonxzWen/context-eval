import type {
  CommandCheck,
  EditableTask,
  ExpectedOutcome,
  HardEvaluation,
  SoftEvaluation,
  SoftRubricItem,
} from '../types';
import { HelpTip } from './HelpTip';

type TaskEditorProps = {
  tasks: EditableTask[];
  selectedTaskIndex: number;
  saveStatus: string;
  serverMode: 'checking' | 'connected' | 'fixture';
  validationErrors: string[];
  onSelectTask: (index: number) => void;
  onUpdateTask: (index: number, task: EditableTask) => void;
  onAddTask: () => void;
  onDuplicateTask: (index: number) => void;
  onDeleteTask: (index: number) => void;
  onSave: () => void;
};

const emptyExpectedOutcome: ExpectedOutcome = {
  summary: '',
  acceptance_points: [],
  files: [],
  forbidden_paths: [],
};

const emptyHardEvaluation: HardEvaluation = {
  enabled: true,
  require_validation_pass: false,
  required_paths: [],
  forbidden_paths: [],
  expected_snippets: [],
  forbidden_snippets: [],
  command_checks: [],
};

const emptySoftEvaluation: SoftEvaluation = {
  enabled: true,
  mode: 'payload-only',
  max_score: 10,
  rubric: [],
};

const categoryOptions = [
  { value: 'bugfix', label: '缺陷修复' },
  { value: 'feature', label: '功能' },
  { value: 'runtime', label: '运行时' },
  { value: 'documentation', label: '文档' },
  { value: 'refactor', label: '重构' },
  { value: 'test', label: '测试' },
  { value: 'gameplay', label: '玩法' },
  { value: 'sample', label: '示例' },
];

const difficultyOptions = [
  { value: 'easy', label: '简单' },
  { value: 'medium', label: '中等' },
  { value: 'hard', label: '困难' },
];

const changeTypeOptions = [
  { value: 'modified', label: '修改' },
  { value: 'created', label: '新增' },
  { value: 'deleted', label: '删除' },
];

export function TaskEditor({
  tasks,
  selectedTaskIndex,
  saveStatus,
  serverMode,
  validationErrors,
  onSelectTask,
  onUpdateTask,
  onAddTask,
  onDuplicateTask,
  onDeleteTask,
  onSave,
}: TaskEditorProps) {
  const task = tasks[selectedTaskIndex];
  if (!task) {
    return (
      <section className="panel task-editor-panel">
        <div className="panel-heading">
          <h2>测试用例</h2>
          <span>0 个用例</span>
        </div>
        <p className="status-line">当前配置没有测试用例。新建一个用例后再保存。</p>
        <button type="button" onClick={onAddTask}>
          新建测试用例
        </button>
      </section>
    );
  }

  const expected = task.expected_outcome || emptyExpectedOutcome;
  const hard = task.hard_evaluation || emptyHardEvaluation;
  const soft = task.soft_evaluation || emptySoftEvaluation;

  function updateTask(patch: Partial<EditableTask>) {
    onUpdateTask(selectedTaskIndex, { ...task, ...patch });
  }

  function updateExpected(patch: Partial<ExpectedOutcome>) {
    updateTask({ expected_outcome: { ...emptyExpectedOutcome, ...expected, ...patch } });
  }

  function updateHard(patch: Partial<HardEvaluation>) {
    updateTask({ hard_evaluation: { ...emptyHardEvaluation, ...hard, ...patch } });
  }

  function updateSoft(patch: Partial<SoftEvaluation>) {
    updateTask({ soft_evaluation: { ...emptySoftEvaluation, ...soft, ...patch } });
  }

  const acceptancePoints = expected.acceptance_points || [];
  const expectedFiles = expected.files || [];
  const validationCommands = task.validation_commands || [];
  const commandChecks = hard.command_checks || [];
  const rubric = soft.rubric || [];

  return (
    <section className="panel task-editor-panel" id="task-config" aria-label="测试用例配置">
      <div className="panel-heading">
        <h2>1 配测试用例</h2>
        <span>{tasks.length} 个用例</span>
      </div>
      <p className="panel-note">只要先填：让 AI 做什么，以及怎样算完成。</p>

      <div className="task-editor-layout">
        <aside className="task-rail" aria-label="测试用例列表">
          {tasks.map((item, index) => {
            const title = item.title?.trim() || item.id?.trim() || `第 ${index + 1} 个用例`;
            const taskId = item.id?.trim();
            const detail = taskId && taskId !== title ? `ID: ${taskId}` : item.category || '';

            return (
              <button
                type="button"
                className={index === selectedTaskIndex ? 'task-tab active' : 'task-tab'}
                key={`${item.id}:${index}`}
                onClick={() => onSelectTask(index)}
              >
                <strong>{title}</strong>
                {detail ? <span>{detail}</span> : null}
              </button>
            );
          })}
          <div className="button-row rail-actions">
            <button type="button" className="secondary" onClick={onAddTask}>
              新建
            </button>
            <button type="button" className="secondary" onClick={() => onDuplicateTask(selectedTaskIndex)}>
              复制
            </button>
            <button
              type="button"
              className="secondary danger-button"
              onClick={() => onDeleteTask(selectedTaskIndex)}
              disabled={tasks.length <= 1}
            >
              删除
            </button>
          </div>
        </aside>

        <form
          className="task-editor-form"
          onSubmit={(event) => {
            event.preventDefault();
            onSave();
          }}
        >
          <fieldset>
            <legend>任务</legend>
            <div className="form-grid simplified-grid">
              <label htmlFor="task-title">
                用例标题
                <input
                  id="task-title"
                  placeholder="例如：修复问候语标点"
                  value={task.title || ''}
                  onChange={(event) => updateTask({ title: event.target.value })}
                />
              </label>
            </div>
            <label htmlFor="task-prompt">
              AI 要做什么
              <textarea
                id="task-prompt"
                aria-label="AI 要做什么"
                placeholder="写给 coding agent 的任务。说明目标、限制和重点即可。"
                value={task.prompt}
                onChange={(event) => updateTask({ prompt: event.target.value })}
              />
            </label>
          </fieldset>

          <fieldset>
            <legend>验收标准</legend>
            <label htmlFor="expected-summary">
              怎样算完成
              <textarea
                id="expected-summary"
                aria-label="怎样算完成"
                placeholder="给人和 AI 仲裁看的成功标准。"
                value={expected.summary || ''}
                onChange={(event) => updateExpected({ summary: event.target.value })}
              />
            </label>
            <ListEditor
              title="检查项"
              values={acceptancePoints}
              placeholder="例如：问候语包含正确标点"
              onChange={(values) => updateExpected({ acceptance_points: values })}
            />
          </fieldset>

          <details className="advanced-inline">
            <summary>更多设置：自动检查 / AI 仲裁</summary>
            <fieldset>
              <legend>自动检查命令</legend>
              <ListEditor
                title="命令"
                values={validationCommands}
                placeholder="python -m pytest"
                onChange={(values) => updateTask({ validation_commands: values })}
              />
            </fieldset>
            <fieldset>
              <legend>用例属性</legend>
              <div className="form-grid">
                <label htmlFor="task-id">
                  <span className="label-with-help">
                    用例 ID
                    <HelpTip text="用于文件名和导出。" />
                  </span>
                  <input
                    id="task-id"
                    value={task.id}
                    onChange={(event) => updateTask({ id: event.target.value })}
                  />
                </label>
                <SegmentedField
                  label="任务分类"
                  value={task.category || ''}
                  options={categoryOptions}
                  onChange={(value) => updateTask({ category: value })}
                />
                <SegmentedField
                  label="难度"
                  value={task.difficulty || ''}
                  options={difficultyOptions}
                  onChange={(value) => updateTask({ difficulty: value })}
                />
              </div>
            </fieldset>
            <fieldset>
              <legend>期望变更文件</legend>
              <ExpectedFileEditor
                files={expectedFiles}
                onChange={(files) => updateExpected({ files })}
              />
            </fieldset>
            <fieldset>
              <legend>硬性检查</legend>
              <p className="field-help">
                确定性检查文件、片段或命令输出；失败时会降低可信度，但它不是综合质量分。
              </p>
              <label className="checkbox-label" htmlFor="hard-enabled">
                <input
                  id="hard-enabled"
                  type="checkbox"
                  checked={hard.enabled}
                  onChange={(event) => updateHard({ enabled: event.target.checked })}
                />
                启用硬性检查
              </label>
              <label className="checkbox-label" htmlFor="require-validation-pass">
                <input
                  id="require-validation-pass"
                  type="checkbox"
                  checked={Boolean(hard.require_validation_pass)}
                  onChange={(event) => updateHard({ require_validation_pass: event.target.checked })}
                />
                要求验证命令通过
              </label>
              <CommandCheckEditor
                checks={commandChecks}
                onChange={(checks) => updateHard({ command_checks: checks })}
              />
            </fieldset>
            <fieldset>
              <legend>AI 仲裁维度</legend>
              <p className="field-help">
                只生成仲裁材料，不自动调用 LLM judge。
              </p>
              <RubricEditor items={rubric} onChange={(items) => updateSoft({ rubric: items })} />
            </fieldset>
            <div className="arbitration-material-note" aria-label="AI 仲裁材料说明">
              <strong>AI 仲裁材料</strong>
              <span>结果页会生成 soft_evaluation_payload.json，供人工或外部 AI 仲裁复核。</span>
            </div>
          </details>

          {validationErrors.length > 0 && (
            <div className="notice validation-notice" role="alert">
              {validationErrors.map((issue) => (
                <div key={issue}>{issue}</div>
              ))}
            </div>
          )}

          <div className="button-row editor-actions">
            <button type="submit" disabled={serverMode !== 'connected'}>
              保存测试用例
            </button>
            <span className="status-line" data-testid="task-save-status">
              {saveStatus}
            </span>
          </div>
        </form>
      </div>
    </section>
  );
}

type ListEditorProps = {
  title: string;
  values: string[];
  placeholder: string;
  helpText?: string;
  onChange: (values: string[]) => void;
};

function ListEditor({ title, values, placeholder, helpText, onChange }: ListEditorProps) {
  return (
    <div className="list-editor">
      <div className="subsection-heading">
        <strong className="label-with-help">
          {title}
          {helpText && <HelpTip text={helpText} />}
        </strong>
        <button type="button" className="secondary compact-button" onClick={() => onChange([...values, ''])}>
          添加
        </button>
      </div>
      {values.map((value, index) => (
        <div className="list-row" key={`${title}:${index}`}>
          <textarea
            aria-label={`${title} ${index + 1}`}
            value={value}
            placeholder={placeholder}
            onChange={(event) => onChange(values.map((item, itemIndex) => (itemIndex === index ? event.target.value : item)))}
          />
          <button
            type="button"
            className="secondary compact-button"
            onClick={() => onChange(values.filter((_, itemIndex) => itemIndex !== index))}
          >
            移除
          </button>
        </div>
      ))}
      {values.length === 0 && <p className="status-line">未添加。</p>}
    </div>
  );
}

type SegmentedFieldProps = {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
};

function SegmentedField({ label, value, options, onChange }: SegmentedFieldProps) {
  const known = options.some((option) => option.value === value);
  return (
    <div className="field-block">
      <span className="field-label">{label}</span>
      <div className="segmented-control" role="radiogroup" aria-label={label}>
        {options.map((option) => (
          <button
            type="button"
            className={option.value === value ? 'segment active' : 'segment'}
            role="radio"
            aria-checked={option.value === value}
            key={option.value}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
        {!known && value && (
          <button type="button" className="segment active" role="radio" aria-checked="true">
            {value}
          </button>
        )}
      </div>
    </div>
  );
}

type ExpectedFileEditorProps = {
  files: NonNullable<ExpectedOutcome['files']>;
  onChange: (files: NonNullable<ExpectedOutcome['files']>) => void;
};

function ExpectedFileEditor({ files, onChange }: ExpectedFileEditorProps) {
  return (
    <div className="list-editor">
      <div className="subsection-heading">
        <strong className="label-with-help">
          期望变更文件
          <HelpTip text="提示应改哪些文件。" />
        </strong>
        <button
          type="button"
          className="secondary compact-button"
          onClick={() => onChange([...files, { path: '', change_type: 'modified', must_change: true }])}
        >
          添加
        </button>
      </div>
      {files.map((file, index) => (
        <div className="structured-row expected-file-row" key={`expected-file:${index}`}>
          <label>
            文件路径
            <input
              aria-label={`期望文件路径 ${index + 1}`}
              value={file.path}
              onChange={(event) =>
                onChange(files.map((item, itemIndex) => (itemIndex === index ? { ...item, path: event.target.value } : item)))
              }
            />
          </label>
          <label>
            变更类型
            <select
              aria-label={`期望文件变更类型 ${index + 1}`}
              value={file.change_type || 'modified'}
              onChange={(event) =>
                onChange(files.map((item, itemIndex) => (itemIndex === index ? { ...item, change_type: event.target.value } : item)))
              }
            >
              {changeTypeOptions.map((option) => (
                <option value={option.value} key={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={Boolean(file.must_change)}
              onChange={(event) =>
                onChange(files.map((item, itemIndex) => (itemIndex === index ? { ...item, must_change: event.target.checked } : item)))
              }
            />
            必须变更
          </label>
          <button
            type="button"
            className="secondary compact-button"
            onClick={() => onChange(files.filter((_, itemIndex) => itemIndex !== index))}
          >
            移除
          </button>
        </div>
      ))}
      {files.length === 0 && <p className="status-line">未指定期望变更文件。</p>}
    </div>
  );
}

type CommandCheckEditorProps = {
  checks: CommandCheck[];
  onChange: (checks: CommandCheck[]) => void;
};

function CommandCheckEditor({ checks, onChange }: CommandCheckEditorProps) {
  return (
    <div className="list-editor">
      <div className="subsection-heading">
        <strong className="label-with-help">
          命令检查
          <HelpTip text="运行命令并匹配输出。" />
        </strong>
        <button
          type="button"
          className="secondary compact-button"
          onClick={() => onChange([...checks, { label: '', command: '', expected: '', timeout_seconds: 60 }])}
        >
          添加
        </button>
      </div>
      {checks.map((check, index) => (
        <div className="structured-row command-check-row" key={`command-check:${index}`}>
          <label>
            名称
            <input
              aria-label={`命令检查名称 ${index + 1}`}
              value={check.label}
              onChange={(event) =>
                onChange(checks.map((item, itemIndex) => (itemIndex === index ? { ...item, label: event.target.value } : item)))
              }
            />
          </label>
          <label>
            命令
            <textarea
              aria-label={`命令检查命令 ${index + 1}`}
              value={check.command}
              onChange={(event) =>
                onChange(checks.map((item, itemIndex) => (itemIndex === index ? { ...item, command: event.target.value } : item)))
              }
            />
          </label>
          <label>
            期望输出
            <input
              aria-label={`命令检查期望输出 ${index + 1}`}
              value={check.expected}
              onChange={(event) =>
                onChange(checks.map((item, itemIndex) => (itemIndex === index ? { ...item, expected: event.target.value } : item)))
              }
            />
          </label>
          <button
            type="button"
            className="secondary compact-button"
            onClick={() => onChange(checks.filter((_, itemIndex) => itemIndex !== index))}
          >
            移除
          </button>
        </div>
      ))}
      {checks.length === 0 && <p className="status-line">未添加命令检查。</p>}
    </div>
  );
}

type RubricEditorProps = {
  items: SoftRubricItem[];
  onChange: (items: SoftRubricItem[]) => void;
};

function RubricEditor({ items, onChange }: RubricEditorProps) {
  return (
    <div className="list-editor">
      <div className="subsection-heading">
        <strong className="label-with-help">
          仲裁维度
          <HelpTip text="AI 仲裁和人工反馈共用。" />
        </strong>
        <button
          type="button"
          className="secondary compact-button"
          onClick={() => onChange([...items, { name: '', description: '', weight: 1 }])}
        >
          添加
        </button>
      </div>
      {items.map((item, index) => (
        <div className="structured-row rubric-row" key={`rubric:${index}`}>
          <label>
            名称
            <input
              aria-label={`评分规则名称 ${index + 1}`}
              value={item.name}
              onChange={(event) =>
                onChange(items.map((entry, itemIndex) => (itemIndex === index ? { ...entry, name: event.target.value } : entry)))
              }
            />
          </label>
          <label>
            说明
            <textarea
              aria-label={`评分规则说明 ${index + 1}`}
              value={item.description}
              onChange={(event) =>
                onChange(items.map((entry, itemIndex) => (itemIndex === index ? { ...entry, description: event.target.value } : entry)))
              }
            />
          </label>
          <label>
            权重
            <input
              aria-label={`评分规则权重 ${index + 1}`}
              type="number"
              min="0.1"
              step="0.1"
              value={item.weight}
              onChange={(event) =>
                onChange(items.map((entry, itemIndex) => (itemIndex === index ? { ...entry, weight: Number(event.target.value) } : entry)))
              }
            />
          </label>
          <button
            type="button"
            className="secondary compact-button"
            onClick={() => onChange(items.filter((_, itemIndex) => itemIndex !== index))}
          >
            移除
          </button>
        </div>
      ))}
      {items.length === 0 && <p className="status-line">未添加评分规则。</p>}
    </div>
  );
}
