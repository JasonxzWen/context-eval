export type AgentProfile = {
  name: string;
  kind: string;
  command: string;
  state: 'ready' | 'needs-check';
};

export type MatrixFixture = {
  agents: AgentProfile[];
  tasks: string[];
  variants: string[];
  trials: number;
  artifacts: string[];
};

export const localAppFixture: MatrixFixture = {
  agents: [
    {
      name: 'coco',
      kind: 'coco',
      command: 'coco -y --query-timeout 10m --bash-tool-timeout 5m -p "{prompt}"',
      state: 'ready',
    },
    {
      name: 'custom',
      kind: 'custom',
      command: 'agent -p {prompt_file}',
      state: 'needs-check',
    },
  ],
  tasks: ['config-round-trip', 'validation-preflight'],
  variants: ['baseline', 'docs-overlay'],
  trials: 1,
  artifacts: ['run_metadata.json', 'run_manifest.json', 'results.jsonl', 'report.md'],
};

export function plannedCaseCount(fixture: MatrixFixture): number {
  return fixture.agents.length * fixture.tasks.length * fixture.variants.length * fixture.trials;
}
