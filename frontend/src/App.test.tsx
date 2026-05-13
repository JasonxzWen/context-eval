import { render, screen } from '@testing-library/react';
import { App } from './App';

describe('App shell', () => {
  it('renders the local app validation shell', () => {
    render(<App />);

    expect(screen.getByTestId('local-app-shell')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Context Eval Local App' })).toBeVisible();
    expect(screen.getByText('Local artifacts only')).toBeVisible();
    expect(screen.getByText('Validation shell')).toBeVisible();
  });

  it('renders deterministic matrix fixture data', () => {
    render(<App />);

    expect(screen.getByTestId('matrix-count')).toHaveTextContent('8');
    expect(screen.getByText('codex-cli')).toBeVisible();
    expect(screen.getByText('traecli')).toBeVisible();
    expect(screen.getByText('results.jsonl')).toBeVisible();
  });
});
