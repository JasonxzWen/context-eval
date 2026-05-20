import type { EditableVariant } from '../types';
import { HelpTip } from './HelpTip';

type VariantEditorProps = {
  variants: EditableVariant[];
  selectedVariantIndex: number;
  saveStatus: string;
  serverMode: 'checking' | 'connected' | 'fixture';
  onSelectVariant: (index: number) => void;
  onUpdateVariants: (variants: EditableVariant[]) => void;
  onSave: () => void;
};

function uniqueVariantName(base: string, variants: EditableVariant[]) {
  const used = new Set(variants.map((variant) => variant.name));
  if (!used.has(base)) return base;
  let suffix = 2;
  while (used.has(`${base}-${suffix}`)) {
    suffix += 1;
  }
  return `${base}-${suffix}`;
}

function blankVariant(variants: EditableVariant[]): EditableVariant {
  return {
    name: uniqueVariantName('new-variant', variants),
    description: '',
    overlays: [{ source: './contexts/new-variant/AGENTS.md', target: 'AGENTS.md' }],
  };
}

function overlayKind(source: string, target: string) {
  const combined = `${source} ${target}`.toLowerCase();
  if (combined.includes('agents.md')) {
    return {
      label: 'Agent 工作说明',
      description: '会作为仓库里的 AGENTS.md 提供给 coding agent。',
      className: 'agent-instructions',
    };
  }
  if (combined.includes('skills')) {
    return {
      label: '技能包',
      description: '会把本地 skills 目录或文件复制到运行工作区。',
      className: 'skills-package',
    };
  }
  return {
    label: '其他上下文资料',
    description: '会按目标路径复制到运行工作区，用作本次方案的一部分。',
    className: 'context-material',
  };
}

export function VariantEditor({
  variants,
  selectedVariantIndex,
  saveStatus,
  serverMode,
  onSelectVariant,
  onUpdateVariants,
  onSave,
}: VariantEditorProps) {
  const selectedIndex = Math.min(selectedVariantIndex, Math.max(variants.length - 1, 0));
  const variant = variants[selectedIndex];

  function updateVariant(patch: Partial<EditableVariant>) {
    if (!variant) return;
    onUpdateVariants(
      variants.map((item, index) => (
        index === selectedIndex ? { ...item, ...patch } : item
      )),
    );
  }

  function updateOverlay(index: number, patch: { source?: string; target?: string }) {
    updateVariant({
      overlays: variant.overlays.map((overlay, overlayIndex) => (
        overlayIndex === index ? { ...overlay, ...patch } : overlay
      )),
    });
  }

  function addVariant() {
    onUpdateVariants([...variants, blankVariant(variants)]);
    onSelectVariant(variants.length);
  }

  function duplicateVariant() {
    if (!variant) return;
    const duplicate = {
      ...structuredClone(variant),
      name: uniqueVariantName(`${variant.name || 'variant'}-copy`, variants),
      description: variant.description ? `${variant.description} 副本` : '',
    };
    onUpdateVariants([...variants, duplicate]);
    onSelectVariant(variants.length);
  }

  function deleteVariant() {
    if (!variant || variants.length <= 1) return;
    if (!window.confirm(`删除上下文方案 "${variant.name}"？`)) return;
    onUpdateVariants(variants.filter((_, index) => index !== selectedIndex));
    onSelectVariant(Math.max(0, selectedIndex - 1));
  }

  return (
    <section className="panel variant-editor-panel" aria-label="上下文方案配置">
      <div className="panel-heading">
        <h2>上下文方案</h2>
        <span>{variants.length} 个方案</span>
      </div>
      <p className="panel-note">
        上下文方案是一组会复制进临时工作区的本地资料。第一版重点比较 `AGENTS.md` 工作说明和
        skills 技能包对同一批测试用例的影响。
      </p>
      {variant ? (
        <div className="editor-split">
          <aside className="task-rail" aria-label="上下文方案列表">
            {variants.map((item, index) => (
              <button
                type="button"
                className={index === selectedIndex ? 'task-tab active' : 'task-tab'}
                key={`${item.name}:${index}`}
                aria-label={`选择上下文方案 ${item.name || index + 1}`}
                onClick={() => onSelectVariant(index)}
              >
                <strong>{item.name || `variant-${index + 1}`}</strong>
                <span>{item.description || `${item.overlays.length} 个上下文资料`}</span>
              </button>
            ))}
            <div className="button-row rail-actions">
              <button type="button" className="secondary" onClick={addVariant}>
                新建
              </button>
              <button type="button" className="secondary" onClick={duplicateVariant}>
                复制
              </button>
              <button
                type="button"
                className="secondary danger-button"
                onClick={deleteVariant}
                disabled={variants.length <= 1}
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
              <label htmlFor="variant-name">
                <span className="label-with-help">
                  方案名称
                  <HelpTip text="用于结果对比的短名称，例如 baseline、agents-v2、skills-added。" />
                </span>
                <input
                  id="variant-name"
                  aria-label="方案名称"
                  value={variant.name}
                  onChange={(event) => updateVariant({ name: event.target.value })}
                />
              </label>
              <label htmlFor="variant-description">
                <span className="label-with-help">
                  方案说明
                  <HelpTip text="给人看的说明：这套 AGENTS.md 或 skills 相比基线改了什么。" />
                </span>
                <textarea
                  id="variant-description"
                  aria-label="方案说明"
                  value={variant.description}
                  onChange={(event) => updateVariant({ description: event.target.value })}
                />
              </label>
            </div>
            <div className="list-editor">
              <div className="subsection-heading">
                <strong className="label-with-help">
                  上下文资料
                  <HelpTip text="从本地读取并复制到运行工作区。常见资料是 AGENTS.md 和 skills，不会读取全局敏感日志或认证信息。" />
                </strong>
                <button
                  type="button"
                  className="secondary compact-button"
                  onClick={() => updateVariant({
                    overlays: [...variant.overlays, { source: '', target: 'AGENTS.md' }],
                  })}
                >
                  添加上下文资料
                </button>
              </div>
              {variant.overlays.map((overlay, index) => {
                const kind = overlayKind(overlay.source, overlay.target);
                return (
                  <div className="overlay-row" key={`${variant.name}:overlay:${index}`}>
                    <div className={`overlay-kind ${kind.className}`}>
                      <strong>{kind.label}</strong>
                      <span>{kind.description}</span>
                    </div>
                    <label htmlFor={`overlay-source-${index}`}>
                      来源路径
                      <input
                        id={`overlay-source-${index}`}
                        aria-label={`上下文资料来源路径 ${index + 1}`}
                        value={overlay.source}
                        onChange={(event) => updateOverlay(index, { source: event.target.value })}
                      />
                    </label>
                    <label htmlFor={`overlay-target-${index}`}>
                      放入项目中的位置
                      <input
                        id={`overlay-target-${index}`}
                        aria-label={`上下文资料目标路径 ${index + 1}`}
                        value={overlay.target}
                        onChange={(event) => updateOverlay(index, { target: event.target.value })}
                      />
                    </label>
                    <button
                      type="button"
                      className="secondary danger-button"
                      onClick={() => updateVariant({
                        overlays: variant.overlays.filter((_, overlayIndex) => overlayIndex !== index),
                      })}
                    >
                      删除
                    </button>
                  </div>
                );
              })}
              {variant.overlays.length === 0 && <p className="status-line">未配置上下文资料。</p>}
            </div>
            <div className="button-row editor-actions">
              <button type="submit" disabled={serverMode !== 'connected'}>
                保存上下文方案
              </button>
              <span className="status-line" data-testid="variant-save-status">
                {saveStatus}
              </span>
            </div>
          </form>
        </div>
      ) : (
        <div className="empty-editor">
          <p className="status-line">当前配置没有上下文方案。</p>
          <button type="button" onClick={addVariant}>
            新建上下文方案
          </button>
        </div>
      )}
    </section>
  );
}
