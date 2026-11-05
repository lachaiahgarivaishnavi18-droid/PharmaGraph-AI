import axios from 'axios';
export const backendPending = import.meta.env.VITE_BACKEND_PENDING === 'true';
export const api = axios.create({ baseURL: (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, ''), timeout: 120000 });
api.interceptors.request.use(config => { if(backendPending) throw new Error('The frontend is online. Backend hosting is pending, so sign-in, uploads, and research are not available yet.'); const token = sessionStorage.getItem('pg-token'); if(token) config.headers.Authorization = `Bearer ${token}`; return config; });
export function errorMessage(error: any): string {
  const detail = error.response?.data?.detail;
  return typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map(x => x.msg).join('; ') : error.message || 'Something went wrong';
}
export function download(name: string, data: unknown) {
  const url = URL.createObjectURL(new Blob([typeof data === 'string' ? data : JSON.stringify(data, null, 2)], {type:'application/json'}));
  const a = document.createElement('a'); a.href=url; a.download=name; a.click(); URL.revokeObjectURL(url);
}
