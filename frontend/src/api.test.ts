import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiRequest } from './api';

function jsonResponse(data: unknown, options: { ok?: boolean; status?: number } = {}) {
  const body = JSON.stringify(data);
  return Promise.resolve({
    ok: options.ok ?? true,
    status: options.status ?? 200,
    text: async () => body,
  } as Response);
}

describe('apiRequest', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('returns 2xx semantic ok:false payloads for endpoints that report check status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        jsonResponse({
          ok: false,
          checks: [{ id: 'codex', label: 'Codex CLI', status: 'error', summary: '未找到 codex' }],
        }),
      ),
    );

    await expect(apiRequest('/api/environment')).resolves.toMatchObject({
      ok: false,
      checks: [{ id: 'codex', summary: '未找到 codex' }],
    });
  });

  it('throws structured errors for non-2xx API responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => jsonResponse({ ok: false, error: 'server validation failed' }, { ok: false, status: 400 })),
    );

    await expect(apiRequest('/api/config/save-editable')).rejects.toThrow('server validation failed');
  });
});
