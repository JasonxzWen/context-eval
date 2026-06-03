import type { ResultCase, ResultsPayload } from './types';

export type ScoreVerdict =
  | 'baseline_wins'
  | 'comparison_wins'
  | 'no_clear_winner'
  | 'evidence_limited';

export type RunScoreCase = {
  case_id: string;
  task_id: string;
  agent_name: string;
  trial_index: number;
  variant: string;
  score: number;
  weighted_score: number;
  scored_weight: number;
  components: RunScoreComponent[];
  confidence: 'high' | 'medium' | 'low';
  evidence_gaps: string[];
};

export type ScoreComponentKey = 'correctness' | 'speed' | 'cost' | 'complexity' | 'change_scope';

export type RunScoreComponent = {
  key: ScoreComponentKey;
  label: string;
  weight: number;
  score: number | null;
  value: number | null;
  evidence_gap?: string;
};

export type RunScoreComparison = {
  group_id: string;
  task_id: string;
  agent_name: string;
  trial_index: number;
  baseline_variant: string;
  comparison_variant: string;
  baseline_case_id: string;
  comparison_case_id: string;
  baseline_score: number;
  comparison_score: number;
  score_delta: number;
  verdict: ScoreVerdict;
  winner_variant: string | null;
  reason: string;
};

export type RunScoreSummary = {
  cases: RunScoreCase[];
  comparisons: RunScoreComparison[];
  recommended_variant: string | null;
  confidence: 'high' | 'medium' | 'low';
  evidence_gaps: string[];
};

export function scoreRunResults(input: ResultsPayload | ResultCase[]): RunScoreSummary {
  const cases = Array.isArray(input) ? input : input.cases;
  const baselineVariant = Array.isArray(input) ? null : input.selected_baseline_variant;
  const scoredCases = scoreCases(cases);
  const scoredByCaseId = new Map(scoredCases.map((scoredCase) => [scoredCase.case_id, scoredCase]));
  const comparisons = compareVariantGroups(cases, scoredByCaseId, baselineVariant || null);
  const evidenceGaps = [...new Set(scoredCases.flatMap((scoredCase) => scoredCase.evidence_gaps))];

  return {
    cases: scoredCases,
    comparisons,
    recommended_variant: recommendedVariant(comparisons),
    confidence: aggregateConfidence(scoredCases.map((scoredCase) => scoredCase.confidence)),
    evidence_gaps: evidenceGaps,
  };
}

function scoreCases(cases: ResultCase[]) {
  const groups = groupCases(cases);
  return [...groups.values()].flatMap((items) => {
    const metricRanges = {
      speed: range(items.map(durationValue)),
      cost: range(items.map(costValue)),
      complexity: range(items.map(complexityValue)),
      change_scope: range(items.map(changedFilesValue)),
    };

    return items.map((result) => scoreCase(result, metricRanges));
  });
}

function scoreCase(
  result: ResultCase,
  metricRanges: Record<Exclude<ScoreComponentKey, 'correctness'>, MetricRange | null>,
): RunScoreCase {
  const correctness = correctnessComponent(result);
  const components: RunScoreComponent[] = [
    correctness,
    relativeComponent({
      key: 'speed',
      label: '速度',
      weight: 12,
      value: durationValue(result),
      range: metricRanges.speed,
      evidenceGap: '缺少结构化耗时，速度不参与评分。',
    }),
    relativeComponent({
      key: 'cost',
      label: '成本',
      weight: 12,
      value: costValue(result),
      range: metricRanges.cost,
      evidenceGap: '缺少结构化 tokens，成本不参与评分。',
    }),
    relativeComponent({
      key: 'complexity',
      label: '操作复杂度',
      weight: 8,
      value: complexityValue(result),
      range: metricRanges.complexity,
      evidenceGap: '缺少结构化 tool calls 和交互轮次，操作复杂度不参与评分。',
    }),
    relativeComponent({
      key: 'change_scope',
      label: '改动面',
      weight: 8,
      value: changedFilesValue(result),
      range: metricRanges.change_scope,
      evidenceGap: '缺少 changed files，改动面不参与评分。',
    }),
  ];
  const componentGaps = components
    .map((component) => component.evidence_gap)
    .filter((gap): gap is string => Boolean(gap));
  const evidenceGaps = [...new Set([...caseEvidenceGaps(result), ...componentGaps])];
  const weightedScore = roundScore(
    components.reduce((total, component) => total + (component.score ?? 0), 0),
  );
  const scoredWeight = components.reduce(
    (total, component) => total + (component.score == null ? 0 : component.weight),
    0,
  );

  return {
    case_id: result.case_id,
    task_id: result.task_id,
    agent_name: result.agent_name,
    trial_index: trialIndex(result),
    variant: result.variant,
    score: scoredWeight > 0 ? roundScore((weightedScore / scoredWeight) * 100) : 0,
    weighted_score: weightedScore,
    scored_weight: scoredWeight,
    components,
    confidence: confidenceFor(evidenceGaps),
    evidence_gaps: evidenceGaps,
  };
}

function compareVariantGroups(
  cases: ResultCase[],
  scoredByCaseId: Map<string, RunScoreCase>,
  requestedBaselineVariant: string | null,
): RunScoreComparison[] {
  const groups = new Map<string, ResultCase[]>();
  cases.forEach((result) => {
    const key = `${result.task_id}\u0000${result.agent_name}\u0000${trialIndex(result)}`;
    groups.set(key, [...(groups.get(key) || []), result]);
  });

  return [...groups.values()].flatMap((items) => {
    if (items.length < 2) return [];
    const baseline = selectBaseline(items, requestedBaselineVariant);
    return items
      .filter((result) => result.case_id !== baseline.case_id)
      .sort((left, right) => left.variant.localeCompare(right.variant))
      .map((comparison) => comparePair(baseline, comparison, scoredByCaseId));
  });
}

function comparePair(
  baseline: ResultCase,
  comparison: ResultCase,
  scoredByCaseId: Map<string, RunScoreCase>,
): RunScoreComparison {
  const baselineScore = scoredByCaseId.get(baseline.case_id)?.score ?? 0;
  const comparisonScore = scoredByCaseId.get(comparison.case_id)?.score ?? 0;
  const baselineFailed = correctnessFailed(baseline);
  const comparisonFailed = correctnessFailed(comparison);
  const group_id = `${baseline.task_id}__${baseline.agent_name}__trial-${trialIndex(
    baseline,
  )}__${baseline.variant}__vs__${comparison.variant}`;

  if (!baselineFailed && comparisonFailed) {
    return {
      group_id,
      task_id: baseline.task_id,
      agent_name: baseline.agent_name,
      trial_index: trialIndex(baseline),
      baseline_variant: baseline.variant,
      comparison_variant: comparison.variant,
      baseline_case_id: baseline.case_id,
      comparison_case_id: comparison.case_id,
      baseline_score: baselineScore,
      comparison_score: comparisonScore,
      score_delta: comparisonScore - baselineScore,
      verdict: 'baseline_wins',
      winner_variant: baseline.variant,
      reason: '正确性未通过的一方不能因为更快或更便宜胜出。',
    };
  }

  if (baselineFailed && !comparisonFailed) {
    return {
      group_id,
      task_id: baseline.task_id,
      agent_name: baseline.agent_name,
      trial_index: trialIndex(baseline),
      baseline_variant: baseline.variant,
      comparison_variant: comparison.variant,
      baseline_case_id: baseline.case_id,
      comparison_case_id: comparison.case_id,
      baseline_score: baselineScore,
      comparison_score: comparisonScore,
      score_delta: comparisonScore - baselineScore,
      verdict: 'comparison_wins',
      winner_variant: comparison.variant,
      reason: '正确性未通过的一方不能因为更快或更便宜胜出。',
    };
  }

  if (Math.abs(comparisonScore - baselineScore) >= 5) {
    const comparisonWins = comparisonScore > baselineScore;
    return {
      group_id,
      task_id: baseline.task_id,
      agent_name: baseline.agent_name,
      trial_index: trialIndex(baseline),
      baseline_variant: baseline.variant,
      comparison_variant: comparison.variant,
      baseline_case_id: baseline.case_id,
      comparison_case_id: comparison.case_id,
      baseline_score: baselineScore,
      comparison_score: comparisonScore,
      score_delta: comparisonScore - baselineScore,
      verdict: comparisonWins ? 'comparison_wins' : 'baseline_wins',
      winner_variant: comparisonWins ? comparison.variant : baseline.variant,
      reason: '双方正确性通过，耗时、成本、操作复杂度或改动面更优的一方胜出。',
    };
  }

  return {
    group_id,
    task_id: baseline.task_id,
    agent_name: baseline.agent_name,
    trial_index: trialIndex(baseline),
    baseline_variant: baseline.variant,
    comparison_variant: comparison.variant,
    baseline_case_id: baseline.case_id,
    comparison_case_id: comparison.case_id,
    baseline_score: baselineScore,
    comparison_score: comparisonScore,
    score_delta: comparisonScore - baselineScore,
    verdict: 'no_clear_winner',
    winner_variant: null,
    reason: '分差未达到明确胜出阈值。',
  };
}

function groupCases(cases: ResultCase[]) {
  const groups = new Map<string, ResultCase[]>();
  cases.forEach((result) => {
    const key = `${result.task_id}\u0000${result.agent_name}\u0000${trialIndex(result)}`;
    groups.set(key, [...(groups.get(key) || []), result]);
  });
  return groups;
}

function selectBaseline(items: ResultCase[], requestedBaselineVariant: string | null) {
  const requested = requestedBaselineVariant
    ? items.find((result) => result.variant === requestedBaselineVariant)
    : null;
  const namedBaseline = items.find((result) => result.variant === 'baseline');
  return requested || namedBaseline || [...items].sort((left, right) => left.variant.localeCompare(right.variant))[0];
}

function correctnessComponent(result: ResultCase): RunScoreComponent {
  const validationScore = result.validation_status === 'passed' ? 20 : 0;
  const hardScore = normalizedEvaluationScore(
    result.hard_evaluation_score,
    result.hard_evaluation_max_score,
    result.hard_evaluation_status,
  );
  const softScore = normalizedEvaluationScore(
    result.soft_evaluation_score,
    result.soft_evaluation_max_score,
    result.soft_evaluation_verdict,
  );
  const knownScores = [validationScore, hardScore, softScore].filter(
    (score): score is number => score != null,
  );

  return {
    key: 'correctness',
    label: '正确性',
    weight: 60,
    score: roundScore(knownScores.reduce((total, score) => total + score, 0)),
    value: null,
    evidence_gap:
      hardScore == null || softScore == null ? '缺少 hard evaluation 或 soft score，正确性证据不完整。' : undefined,
  };
}

function normalizedEvaluationScore(
  score: number | null | undefined,
  maxScore: number | null | undefined,
  statusOrVerdict: string | null | undefined,
) {
  if (score != null && maxScore != null && maxScore > 0) {
    return clamp((score / maxScore) * 20, 0, 20);
  }
  if (statusOrVerdict === 'passed' || statusOrVerdict === 'pass') return 20;
  if (statusOrVerdict === 'failed' || statusOrVerdict === 'fail') return 0;
  return null;
}

type MetricRange = {
  min: number;
  max: number;
};

function relativeComponent({
  key,
  label,
  weight,
  value,
  range: metricRange,
  evidenceGap,
}: {
  key: Exclude<ScoreComponentKey, 'correctness'>;
  label: string;
  weight: number;
  value: number | null;
  range: MetricRange | null;
  evidenceGap: string;
}): RunScoreComponent {
  if (value == null || metricRange == null) {
    return { key, label, weight, value, score: null, evidence_gap: evidenceGap };
  }
  if (metricRange.max === metricRange.min) {
    return { key, label, weight, value, score: weight };
  }
  if (value <= 0) {
    return { key, label, weight, value, score: metricRange.min <= 0 ? weight : 0 };
  }
  return {
    key,
    label,
    weight,
    value,
    score: roundScore(clamp(weight * (metricRange.min / value), 0, weight)),
  };
}

function range(values: Array<number | null>): MetricRange | null {
  const knownValues = values.filter((value): value is number => value != null);
  if (knownValues.length === 0) return null;
  return {
    min: Math.min(...knownValues),
    max: Math.max(...knownValues),
  };
}

function durationValue(result: ResultCase) {
  return finiteNumber(result.agent_duration_seconds);
}

function costValue(result: ResultCase) {
  const totalTokens = finiteNumber(result.total_tokens);
  if (totalTokens == null) return null;
  const reasoningTokens = finiteNumber(result.reasoning_tokens);
  const cachedInputTokens = finiteNumber(result.cached_input_tokens);
  return Math.max(0, totalTokens + (reasoningTokens ?? 0) - (cachedInputTokens ?? 0) * 0.25);
}

function toolCallValue(result: ResultCase) {
  return finiteNumber(result.tool_call_count);
}

function interactionTurnValue(result: ResultCase) {
  return finiteNumber(result.interaction_turn_count);
}

function complexityValue(result: ResultCase) {
  const toolCalls = toolCallValue(result);
  const interactionTurns = interactionTurnValue(result);
  if (toolCalls == null && interactionTurns == null) return null;
  return (toolCalls ?? 0) + (interactionTurns ?? 0);
}

function changedFilesValue(result: ResultCase) {
  return finiteNumber(result.changed_files);
}

function finiteNumber(value: number | null | undefined) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function caseEvidenceGaps(result: ResultCase) {
  const gaps: string[] = [];
  if ((result.telemetry_status || 'unavailable') !== 'collected') {
    gaps.push('telemetry 未完整采集，耗时、tokens 和工具调用不参与资源评分。');
  }
  (result.telemetry_evidence_gaps || []).forEach((gap) => {
    gaps.push(`telemetry 证据缺口：${gap}`);
  });
  if (result.telemetry_source === 'codex-jsonl' && !result.codex_events_path) {
    gaps.push('缺少 codex-jsonl 事件文件路径。');
  }
  if (result.telemetry_source === 'codex-jsonl' && !result.codex_final_message_path) {
    gaps.push('缺少 codex final message 路径。');
  }
  if (result.telemetry_source === 'codex-jsonl' && interactionTurnValue(result) == null) {
    gaps.push('缺少结构化交互轮次，操作复杂度只使用已采集指标。');
  }
  return gaps;
}

function correctnessFailed(result: ResultCase) {
  return (
    result.validation_status !== 'passed' ||
    result.hard_evaluation_status === 'failed' ||
    result.soft_evaluation_verdict === 'fail'
  );
}

function confidenceFor(evidenceGaps: string[]): 'high' | 'medium' | 'low' {
  if (evidenceGaps.some((gap) => gap.includes('telemetry 未完整采集'))) return 'low';
  if (evidenceGaps.length > 0) return 'medium';
  return 'high';
}

function trialIndex(result: ResultCase) {
  if (typeof result.trial_index === 'number' && Number.isInteger(result.trial_index)) {
    return result.trial_index;
  }
  const match = result.case_id.match(/(?:^|__)trial-(\d+)(?:__|$)/);
  return match ? Number(match[1]) : 0;
}

function roundScore(value: number) {
  return Math.round(value * 10) / 10;
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function recommendedVariant(comparisons: RunScoreComparison[]) {
  const wins = new Map<string, number>();
  comparisons.forEach((comparison) => {
    if (comparison.winner_variant) {
      wins.set(comparison.winner_variant, (wins.get(comparison.winner_variant) || 0) + 1);
    }
  });
  const ranked = [...wins.entries()].sort((left, right) => right[1] - left[1]);
  return ranked[0]?.[0] || null;
}

function aggregateConfidence(confidences: Array<'high' | 'medium' | 'low'>) {
  if (confidences.includes('low')) return 'low';
  if (confidences.includes('medium')) return 'medium';
  return 'high';
}
