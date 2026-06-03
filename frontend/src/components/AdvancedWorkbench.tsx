import type { ReactNode } from 'react';

type AdvancedWorkbenchProps = {
  children: ReactNode;
};

export function AdvancedWorkbench({ children }: AdvancedWorkbenchProps) {
  return (
    <section className="content-grid" data-testid="advanced-workbench" aria-label="高级工作台">
      {children}
    </section>
  );
}
