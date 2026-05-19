type WorkflowBandProps = {
  steps: [string, string][];
};

export function WorkflowBand({ steps }: WorkflowBandProps) {
  return (
    <section className="workflow-band" aria-label="工作流状态">
      {steps.map(([label, state]) => (
        <div className="workflow-step" key={label}>
          <span>{label}</span>
          <strong>{state}</strong>
        </div>
      ))}
    </section>
  );
}
