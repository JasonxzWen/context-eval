import { useMemo } from 'react';
import { scoreRunResults } from '../scoring';
import type { ResultCase, ResultsPayload } from '../types';

type RunScoreSummaryProps = {
  results: ResultsPayload;
  onViewEvidence: () => void;
};

const confidenceLabels: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
};

function formatScore(value: number | null | undefined) {
  return value == null ? '-' : value.toFixed(1);
}

function formatDuration(value: number | null | undefined) {
  return value == null ? '-' : `${value.toFixed(1)}s`;
}

function metricValue(value: number | null | undefined) {
  return value == null ? '-' : String(value);
}

function collectedMetricValue(value: number | null | undefined) {
  return value == null ? '未采集' : String(value);
}

function winnerText(winner: string | null) {
  return winner ? `推荐方案：${winner}` : '无明显胜出';
}

function caseById(cases: ResultCase[], caseId: string | undefined) {
  return cases.find((result) => result.case_id === caseId) || null;
}

export function RunScoreSummary({ results, onViewEvidence }: RunScoreSummaryProps) {
  const summary = useMemo(() => scoreRunResults(results), [results]);
  const firstComparison = summary.comparisons[0] || null;
  const baselineScore = firstComparison
    ? firstComparison.baseline_score
    : summary.cases.find((result) => result.variant === 'baseline')?.score;
  const experimentScore = firstComparison
    ? firstComparison.comparison_score
    : summary.cases.find((result) => result.variant !== 'baseline')?.score;
  const baselineCase = firstComparison ? caseById(results.cases, firstComparison.baseline_case_id) : null;
  const experimentCase = firstComparison ? caseById(results.cases, firstComparison.comparison_case_id) : null;
  const recommended = firstComparison ? firstComparison.winner_variant : summary.recommended_variant;

  return (
    <section className="run-score-summary" aria-label="极简结论">
      <div className="score-summary-heading">
        <div>
          <p className="eyebrow">极简结论</p>
          <h2>综合分</h2>
        </div>
        <strong>{winnerText(recommended)}</strong>
      </div>

      <div className="score-pair-grid">
        <article>
          <span>baseline score</span>
          <strong>{formatScore(baselineScore)}</strong>
          <small>{baselineCase?.variant || 'baseline'}</small>
        </article>
        <article>
          <span>experiment score</span>
          <strong>{formatScore(experimentScore)}</strong>
          <small>{experimentCase?.variant || firstComparison?.comparison_variant || 'experiment'}</small>
        </article>
      </div>

      <dl className="score-metric-grid">
        <div>
          <dt>耗时</dt>
          <dd>
            {formatDuration(baselineCase?.agent_duration_seconds)} /{' '}
            {formatDuration(experimentCase?.agent_duration_seconds)}
          </dd>
        </div>
        <div>
          <dt>tokens</dt>
          <dd>
            {metricValue(baselineCase?.total_tokens)} / {metricValue(experimentCase?.total_tokens)}
          </dd>
        </div>
        <div>
          <dt>tool calls</dt>
          <dd>
            {metricValue(baselineCase?.tool_call_count)} /{' '}
            {metricValue(experimentCase?.tool_call_count)}
          </dd>
        </div>
        <div>
          <dt>交互轮次</dt>
          <dd>
            {collectedMetricValue(baselineCase?.interaction_turn_count)} /{' '}
            {collectedMetricValue(experimentCase?.interaction_turn_count)}
          </dd>
        </div>
        <div>
          <dt>修改文件</dt>
          <dd>
            {metricValue(baselineCase?.changed_files)} / {metricValue(experimentCase?.changed_files)}
          </dd>
        </div>
        <div>
          <dt>证据可信度</dt>
          <dd>{confidenceLabels[summary.confidence] || summary.confidence}</dd>
        </div>
      </dl>

      {summary.evidence_gaps.length > 0 && (
        <div className="score-evidence-note" role="status">
          证据不完整：{summary.evidence_gaps.slice(0, 2).join('；')}
        </div>
      )}

      <button type="button" className="secondary" onClick={onViewEvidence}>
        查看完整证据
      </button>
    </section>
  );
}
