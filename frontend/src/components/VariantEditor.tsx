import type { EditableVariant } from '../types';
import { HelpTip } from './HelpTip';

type VariantEditorProps = {
  variants: EditableVariant[];
  selectedVariantIndex: number;
  saveStatus: string;
  serverMode: 'checking' | 'connected' | 'fixture';
  validationErrors: string[];
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

function displayVariantTitle(variant: EditableVariant, index: number) {
  if (variant.name === 'baseline') return '当前默认资料包';
  return variant.description?.trim() || variant.name?.trim() || `第 ${index + 1} 个资料包`;
}

function displayVariantDetail(variant: EditableVariant, title: string) {
  const name = variant.name?.trim();
  if (name && name !== title) return `ID: ${name}`;
  return `${variant.overlays.length} 份资料`;
}

function overlayKind(source: string, target: string) {
  const combined = `${source} ${target}`.toLowerCase();
  if (combined.includes('agents.md')) {
    return {
      label: 'AI 工作说明',
      description: 'AGENTS.md',
      className: 'agent-instructions',
    };
  }
  if (combined.includes('skills')) {
    return {
      label: '技能包',
      description: 'skills',
      className: 'skills-package',
    };
  }
  return {
    label: '其他资料',
    description: '本地文件',
    className: 'context-material',
  };
}

export function VariantEditor({
  variants,
  selectedVariantIndex,
  saveStatus,
  serverMode,
  validationErrors,
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
    <section className="panel variant-editor-panel" id="context-config" aria-label="对比资料包配置">
      <div className="panel-heading">
        <h2>2 配给 AI 的资料包</h2>
        <span>{variants.length} 个资料包</span>
      </div>
      <p className="panel-note">
        一个资料包就是一套会交给 coding agent 的本地说明，通常包含 AGENTS.md 和 skills。准备“当前默认”和“实验版本”，用同一批测试用例比较哪套效果更好。
      </p>
      {variant ? (
        <div className="editor-split">
          <aside className="task-rail" aria-label="资料包列表">
            {variants.map((item, index) => {
              const title = displayVariantTitle(item, index);
              return (
                <button
                  type="button"
                  className={index === selectedIndex ? 'task-tab active' : 'task-tab'}
                  key={`${item.name}:${index}`}
                  aria-label={`选择资料包 ${item.name || index + 1}`}
                  onClick={() => onSelectVariant(index)}
                >
                  <strong>{title}</strong>
                  <span>{displayVariantDetail(item, title)}</span>
                </button>
              );
            })}
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
            <div className="form-grid simplified-grid">
              <label htmlFor="variant-name">
                <span className="label-with-help">
                  资料包 ID
                  <HelpTip text="结果文件和对比表使用。" />
                </span>
                <input
                  id="variant-name"
                  aria-label="资料包 ID"
                  value={variant.name}
                  onChange={(event) => updateVariant({ name: event.target.value })}
                />
              </label>
              <label htmlFor="variant-description">
                <span className="label-with-help">
                  给人看的说明
                  <HelpTip text="写清默认包或实验改动。" />
                </span>
                <textarea
                  id="variant-description"
                  aria-label="给人看的说明"
                  value={variant.description}
                  onChange={(event) => updateVariant({ description: event.target.value })}
                />
              </label>
            </div>
            <div className="list-editor">
              <div className="subsection-heading">
                <strong className="label-with-help">
                  资料包内容
                  <HelpTip text="本地 AGENTS.md / skills。" />
                </strong>
                <button
                  type="button"
                  className="secondary compact-button"
                  onClick={() => updateVariant({
                    overlays: [...variant.overlays, { source: '', target: 'AGENTS.md' }],
                  })}
                >
                  添加资料
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
                      本地文件或文件夹
                      <input
                        id={`overlay-source-${index}`}
                        aria-label={`资料来源路径 ${index + 1}`}
                        value={overlay.source}
                        onChange={(event) => updateOverlay(index, { source: event.target.value })}
                      />
                    </label>
                    <details className="overlay-advanced">
                      <summary>放置位置</summary>
                      <label htmlFor={`overlay-target-${index}`}>
                        放到运行项目里的位置
                        <input
                          id={`overlay-target-${index}`}
                          aria-label={`资料目标路径 ${index + 1}`}
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
                    </details>
                  </div>
                );
              })}
              {variant.overlays.length === 0 && <p className="status-line">未添加资料。</p>}
            </div>
            {validationErrors.length > 0 && (
              <div className="notice validation-notice" role="alert">
                {validationErrors.map((issue) => (
                  <div key={issue}>{issue}</div>
                ))}
              </div>
            )}
            <div className="button-row editor-actions">
              <button type="submit" disabled={serverMode !== 'connected'}>
                保存资料包
              </button>
              <span className="status-line" data-testid="variant-save-status">
                {saveStatus}
              </span>
            </div>
          </form>
        </div>
      ) : (
        <div className="empty-editor">
          <p className="status-line">当前配置没有资料包。</p>
          <button type="button" onClick={addVariant}>
            新建资料包
          </button>
        </div>
      )}
    </section>
  );
}
