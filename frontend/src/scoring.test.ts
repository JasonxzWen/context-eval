import { describe, expect, it } from 'vitest';
import { scoreRunResults } from './scoring';
import type { ResultCase } from './types';

function caseResult(overrides: Partial<ResultCase>): ResultCase {
  return {
    case_id: `${overrides.task_id ?? 'task'}__${overrides.variant ?? 'baseline'}__${
      overrides.agent_name ?? 'codex'
    }`,
    agent_name: 'codex',
    task_id: 'task',
    variant: 'baseline',
    trial_index: 1,
    status: 'completed',
    validation_status: 'passed',
    confidence: 'high',
    telemetry_status: 'collected',
    telemetry_source: 'codex-jsonl',
    telemetry_evidence_gaps: [],
    codex_events_path: 'artifacts/task__baseline__codex/codex-events.jsonl',
    codex_final_message_path: 'artifacts/task__baseline__codex/codex-final-message.md',
    agent_duration_seconds: 60,
    total_tokens: 1000,
    reasoning_tokens: 100,
    cached_input_tokens: 0,
    tool_call_count: 4,
    interaction_turn_count: 1,
    changed_files: 2,
    hard_evaluation_status: 'passed',
    hard_evaluation_score: 4,
    hard_evaluation_max_score: 4,
    soft_evaluation_status: 'result_available',
    soft_evaluation_score: 8,
    soft_evaluation_max_score: 10,
    soft_evaluation_verdict: 'pass',
    ...overrides,
  };
}

describe('scoreRunResults', () => {
  it('chooses the passing variant over a failed variant even when the failed run is cheaper', () => {
    const summary = scoreRunResults([
      caseResult({ variant: 'baseline' }),
      caseResult({
        variant: 'experiment',
        validation_status: 'failed',
        hard_evaluation_status: 'failed',
        hard_evaluation_score: 0,
        agent_duration_seconds: 1,
        total_tokens: 1,
        reasoning_tokens: 0,
        tool_call_count: 0,
        changed_files: 0,
      }),
    ]);

    expect(summary.comparisons).toHaveLength(1);
    expect(summary.comparisons[0]).toMatchObject({
      verdict: 'baseline_wins',
      winner_variant: 'baseline',
      reason: '正确性未通过的一方不能因为更快或更便宜胜出。',
    });
  });

  it('prefers the passing variant with lower duration, tokens, tool calls, and change scope', () => {
    const summary = scoreRunResults([
      caseResult({
        variant: 'baseline',
        agent_duration_seconds: 120,
        total_tokens: 2000,
        reasoning_tokens: 400,
        tool_call_count: 12,
        changed_files: 8,
      }),
      caseResult({
        variant: 'experiment',
        agent_duration_seconds: 45,
        total_tokens: 900,
        reasoning_tokens: 100,
        tool_call_count: 3,
        changed_files: 2,
      }),
    ]);

    expect(summary.comparisons[0]).toMatchObject({
      verdict: 'comparison_wins',
      winner_variant: 'experiment',
    });
    expect(summary.comparisons[0].comparison_score).toBeGreaterThan(
      summary.comparisons[0].baseline_score,
    );
    expect(summary.comparisons[0].reason).toContain('耗时、成本、操作复杂度或改动面更优');
  });

  it('uses interaction turn counts as part of operation complexity', () => {
    const summary = scoreRunResults([
      caseResult({
        variant: 'baseline',
        tool_call_count: 2,
        interaction_turn_count: 98,
      }),
      caseResult({
        variant: 'experiment',
        tool_call_count: 2,
        interaction_turn_count: 1,
      }),
    ]);

    expect(summary.comparisons[0]).toMatchObject({
      verdict: 'comparison_wins',
      winner_variant: 'experiment',
    });
    expect(summary.comparisons[0].score_delta).toBeGreaterThanOrEqual(5);
    const baselineComplexity = summary.cases
      .find((scoredCase) => scoredCase.variant === 'baseline')
      ?.components.find((component) => component.key === 'complexity');
    const experimentComplexity = summary.cases
      .find((scoredCase) => scoredCase.variant === 'experiment')
      ?.components.find((component) => component.key === 'complexity');
    expect(baselineComplexity?.value).toBe(100);
    expect(experimentComplexity?.value).toBe(3);
    expect(experimentComplexity?.score ?? 0).toBeGreaterThan(baselineComplexity?.score ?? 0);
  });

  it('reports no clear winner when the composite score delta is below five points', () => {
    const summary = scoreRunResults([
      caseResult({
        variant: 'baseline',
        agent_duration_seconds: 100,
        total_tokens: 1000,
        reasoning_tokens: 100,
        tool_call_count: 4,
        changed_files: 2,
      }),
      caseResult({
        variant: 'experiment',
        agent_duration_seconds: 99,
        total_tokens: 990,
        reasoning_tokens: 100,
        tool_call_count: 4,
        changed_files: 2,
      }),
    ]);

    expect(Math.abs(summary.comparisons[0].score_delta)).toBeLessThan(5);
    expect(summary.comparisons[0]).toMatchObject({
      verdict: 'no_clear_winner',
      winner_variant: null,
      reason: '分差未达到明确胜出阈值。',
    });
  });

  it('lowers confidence and leaves resource components unscored when telemetry is missing', () => {
    const summary = scoreRunResults([
      caseResult({
        telemetry_status: 'unavailable',
        telemetry_source: 'none',
        agent_duration_seconds: null,
        total_tokens: null,
        reasoning_tokens: null,
        cached_input_tokens: null,
        tool_call_count: null,
        interaction_turn_count: null,
      }),
    ]);
    const scoredCase = summary.cases[0];

    expect(summary.confidence).toBe('low');
    expect(scoredCase.confidence).toBe('low');
    expect(scoredCase.evidence_gaps).toContain(
      'telemetry 未完整采集，耗时、tokens 和工具调用不参与资源评分。',
    );
    expect(scoredCase.components.find((component) => component.key === 'speed')?.score).toBeNull();
    expect(scoredCase.components.find((component) => component.key === 'cost')?.score).toBeNull();
    expect(scoredCase.components.find((component) => component.key === 'complexity')?.score).toBeNull();
  });

  it('records an evidence gap instead of treating missing interaction turns as zero', () => {
    const summary = scoreRunResults([
      caseResult({
        interaction_turn_count: null,
        tool_call_count: 4,
      }),
    ]);
    const scoredCase = summary.cases[0];
    const complexity = scoredCase.components.find((component) => component.key === 'complexity');

    expect(scoredCase.confidence).toBe('medium');
    expect(scoredCase.evidence_gaps).toContain('缺少结构化交互轮次，操作复杂度只使用已采集指标。');
    expect(complexity?.value).toBe(4);
    expect(complexity?.score).not.toBeNull();
  });

  it('uses hard and soft evaluation scores as part of correctness', () => {
    const summary = scoreRunResults([
      caseResult({
        variant: 'baseline',
        soft_evaluation_score: 6,
        soft_evaluation_max_score: 10,
      }),
      caseResult({
        variant: 'experiment',
        soft_evaluation_score: 9,
        soft_evaluation_max_score: 10,
      }),
    ]);
    const baselineCorrectness = summary.cases
      .find((scoredCase) => scoredCase.variant === 'baseline')
      ?.components.find((component) => component.key === 'correctness')?.score;
    const experimentCorrectness = summary.cases
      .find((scoredCase) => scoredCase.variant === 'experiment')
      ?.components.find((component) => component.key === 'correctness')?.score;

    expect(experimentCorrectness).toBeGreaterThan(baselineCorrectness ?? 0);
    expect(summary.comparisons[0]).toMatchObject({
      verdict: 'comparison_wins',
      winner_variant: 'experiment',
    });
    expect(summary.comparisons[0].score_delta).toBeGreaterThanOrEqual(5);
  });

  it('compares variants only within the same structured trial index', () => {
    const summary = scoreRunResults([
      caseResult({ case_id: 'task__baseline__codex__first', variant: 'baseline', trial_index: 1 }),
      caseResult({
        case_id: 'task__experiment__codex__first',
        variant: 'experiment',
        trial_index: 1,
      }),
      caseResult({ case_id: 'task__baseline__codex__second', variant: 'baseline', trial_index: 2 }),
      caseResult({
        case_id: 'task__experiment__codex__second',
        variant: 'experiment',
        trial_index: 2,
      }),
    ]);

    expect(summary.comparisons).toHaveLength(2);
    expect(summary.comparisons.map((comparison) => comparison.trial_index)).toEqual([1, 2]);
  });
});
