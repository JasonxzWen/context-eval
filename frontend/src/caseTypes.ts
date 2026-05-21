import type { TaskCaseType } from './types';

export const caseTypeOptions: { value: TaskCaseType; label: string }[] = [
  { value: 'compile_diagnosis', label: '编译报错' },
  { value: 'bugfix', label: '修 Bug' },
  { value: 'incident', label: '线上故障' },
  { value: 'feature', label: '新功能' },
  { value: 'custom', label: '自定义' },
];

const caseTypeLabels: Record<TaskCaseType, string> = Object.fromEntries(
  caseTypeOptions.map((item) => [item.value, item.label]),
) as Record<TaskCaseType, string>;

export function formatCaseType(value: TaskCaseType | string | null | undefined) {
  if (!value) return caseTypeLabels.custom;
  return caseTypeLabels[value as TaskCaseType] ?? value;
}
