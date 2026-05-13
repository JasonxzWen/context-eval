import { expect, test } from '@playwright/test';

test('renders the fixture-backed local app shell', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Context Eval Local App' })).toBeVisible();
  await expect(page.getByText('Local artifacts only')).toBeVisible();
  await expect(page.getByTestId('matrix-count')).toHaveText('8');
  await expect(page.getByText('traecli', { exact: true })).toBeVisible();

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  );
  expect(hasHorizontalOverflow).toBe(false);
});
