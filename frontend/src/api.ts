export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });
  const text = await response.text();
  let data: Record<string, unknown> = {};
  let parseError = false;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    parseError = true;
    data = { error: text || `请求失败: ${response.status}` };
  }
  if (parseError || !response.ok) {
    throw new Error(typeof data.error === 'string' ? data.error : `请求失败: ${response.status}`);
  }
  return data as T;
}
