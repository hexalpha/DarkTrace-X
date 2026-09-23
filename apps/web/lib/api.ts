let refreshing: Promise<boolean> | undefined;
function csrf() { return document.cookie.split('; ').find(c => c.startsWith('dtx_csrf='))?.slice(9) ?? ''; }
export async function apiFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const send = () => fetch(url, { ...init, credentials: 'include', headers: { 'Content-Type': 'application/json', ...init.headers, 'X-CSRF-Token': csrf() } });
  let response = await send();
  if (response.status === 401 && !['/auth/login','/auth/register','/auth/refresh','/auth/logout'].some(p=>url.endsWith(p))) {
    const root = url.split('/api/v1')[0];
    if (!refreshing) refreshing = fetch(root+'/api/v1/auth/refresh', {method:'POST', credentials:'include', headers:{'X-CSRF-Token':csrf()}}).then(r=>r.ok).catch(()=>false).finally(()=>{refreshing=undefined;});
    if (await refreshing) response = await send();
  }
  if (response.status === 401 && !url.endsWith('/auth/login')) window.dispatchEvent(new Event('darktracex:expired'));
  return response;
}
export async function apiRequest<T>(base: string, path: string, init: RequestInit = {}): Promise<T> {
  const response = await apiFetch(`${base}/api/v1${path}`, init);
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : Array.isArray(data?.detail) ? data.detail.map((e: {msg: string}) => e.msg).join('; ') : data?.detail?.message ?? 'Service unavailable. Please retry.');
  return data as T;
}
