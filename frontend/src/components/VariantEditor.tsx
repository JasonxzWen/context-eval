import type { EditableVariant } from '../types';

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
    if (!window.confirm(`删除上下文版本 "${variant.name}"？`)) return;
    onUpdateVariants(variants.filter((_, index) => index !== selectedIndex));
    onSelectVariant(Math.max(0, selectedIndex - 1));
  }

  return (
    <section className="panel variant-editor-panel" aria-label="上下文版本配置">
      <div className="panel-heading">
        <h2>上下文版本</h2>
        <span>{variants.length}</span>
      </div>
      {variant ? (
        <div className="editor-split">
          <aside className="task-rail" aria-label="上下文版本列表">
            {variants.map((item, index) => (
              <button
                type="button"
                className={index === selectedIndex ? 'task-tab active' : 'task-tab'}
                key={`${item.name}:${index}`}
                aria-label={`选择上下文版本 ${item.name || index + 1}`}
                onClick={() => onSelectVariant(index)}
              >
                <strong>{item.name || `variant-${index + 1}`}</strong>
                <span>{item.description || `${item.overlays.length} 个覆盖文件`}</span>
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
                版本名称
                <input
                  id="variant-name"
                  aria-label="版本名称"
                  value={variant.name}
                  onChange={(event) => updateVariant({ name: event.target.value })}
                />
              </label>
              <label htmlFor="variant-description">
                版本说明
                <textarea
                  id="variant-description"
                  aria-label="版本说明"
                  value={variant.description}
                  onChange={(event) => updateVariant({ description: event.target.value })}
                />
              </label>
            </div>
            <div className="list-editor">
              <div className="subsection-heading">
                <strong>覆盖文件</strong>
                <button
                  type="button"
                  className="secondary compact-button"
                  onClick={() => updateVariant({
                    overlays: [...variant.overlays, { source: '', target: 'AGENTS.md' }],
                  })}
                >
                  添加覆盖文件
                </button>
              </div>
              {variant.overlays.map((overlay, index) => (
                <div className="overlay-row" key={`${variant.name}:overlay:${index}`}>
                  <label htmlFor={`overlay-source-${index}`}>
                    来源路径
                    <input
                      id={`overlay-source-${index}`}
                      aria-label={`覆盖文件来源路径 ${index + 1}`}
                      value={overlay.source}
                      onChange={(event) => updateOverlay(index, { source: event.target.value })}
                    />
                  </label>
                  <label htmlFor={`overlay-target-${index}`}>
                    目标路径
                    <input
                      id={`overlay-target-${index}`}
                      aria-label={`覆盖文件目标路径 ${index + 1}`}
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
              ))}
              {variant.overlays.length === 0 && <p className="status-line">未配置覆盖文件。</p>}
            </div>
            <div className="button-row editor-actions">
              <button type="submit" disabled={serverMode !== 'connected'}>
                保存上下文版本
              </button>
              <span className="status-line" data-testid="variant-save-status">
                {saveStatus}
              </span>
            </div>
          </form>
        </div>
      ) : (
        <div className="empty-editor">
          <p className="status-line">当前配置没有上下文版本。</p>
          <button type="button" onClick={addVariant}>
            新建上下文版本
          </button>
        </div>
      )}
    </section>
  );
}
