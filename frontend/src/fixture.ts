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
      name: 'codex',
      kind: 'codex-cli',
      command: 'codex exec -C {workspace} - < {prompt_file}',
      state: 'ready',
    },
    {
      name: 'trae',
      kind: 'traecli',
      command: 'traecli -p "{prompt}"',
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
