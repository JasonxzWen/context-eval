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
      description: variant.description ? `${variant.description} copy` : '',
    };
    onUpdateVariants([...variants, duplicate]);
    onSelectVariant(variants.length);
  }

  function deleteVariant() {
    if (!variant || variants.length <= 1) return;
    if (!window.confirm(`删除 variant "${variant.name}"？`)) return;
    onUpdateVariants(variants.filter((_, index) => index !== selectedIndex));
    onSelectVariant(Math.max(0, selectedIndex - 1));
  }

  return (
    <section className="panel variant-editor-panel" aria-label="Context variants">
      <div className="panel-heading">
        <h2>Context Variants</h2>
        <span>{variants.length}</span>
      </div>
      {variant ? (
        <div className="editor-split">
          <aside className="task-rail" aria-label="variant 列表">
            {variants.map((item, index) => (
              <button
                type="button"
                className={index === selectedIndex ? 'task-tab active' : 'task-tab'}
                key={`${item.name}:${index}`}
                aria-label={`选择 variant ${item.name || index + 1}`}
                onClick={() => onSelectVariant(index)}
              >
                <strong>{item.name || `variant-${index + 1}`}</strong>
                <span>{item.description || `${item.overlays.length} overlay(s)`}</span>
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
                variant name
                <input
                  id="variant-name"
                  aria-label="variant name"
                  value={variant.name}
                  onChange={(event) => updateVariant({ name: event.target.value })}
                />
              </label>
              <label htmlFor="variant-description">
                description
                <textarea
                  id="variant-description"
                  aria-label="variant description"
                  value={variant.description}
                  onChange={(event) => updateVariant({ description: event.target.value })}
                />
              </label>
            </div>
            <div className="list-editor">
              <div className="subsection-heading">
                <strong>overlays</strong>
                <button
                  type="button"
                  className="secondary compact-button"
                  onClick={() => updateVariant({
                    overlays: [...variant.overlays, { source: '', target: 'AGENTS.md' }],
                  })}
                >
                  添加 overlay
                </button>
              </div>
              {variant.overlays.map((overlay, index) => (
                <div className="overlay-row" key={`${variant.name}:overlay:${index}`}>
                  <label htmlFor={`overlay-source-${index}`}>
                    source
                    <input
                      id={`overlay-source-${index}`}
                      aria-label={`overlay source ${index + 1}`}
                      value={overlay.source}
                      onChange={(event) => updateOverlay(index, { source: event.target.value })}
                    />
                  </label>
                  <label htmlFor={`overlay-target-${index}`}>
                    target
                    <input
                      id={`overlay-target-${index}`}
                      aria-label={`overlay target ${index + 1}`}
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
              {variant.overlays.length === 0 && <p className="status-line">未配置 overlay。</p>}
            </div>
            <div className="button-row editor-actions">
              <button type="submit" disabled={serverMode !== 'connected'}>
                保存 variant 配置
              </button>
              <span className="status-line" data-testid="variant-save-status">
                {saveStatus}
              </span>
            </div>
          </form>
        </div>
      ) : (
        <div className="empty-editor">
          <p className="status-line">当前配置没有 context variant。</p>
          <button type="button" onClick={addVariant}>
            新建 variant
          </button>
        </div>
      )}
    </section>
  );
}
