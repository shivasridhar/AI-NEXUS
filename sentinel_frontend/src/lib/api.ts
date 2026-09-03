import { useGlobalStore } from './store';

const rawUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const BASE_URL = rawUrl.endsWith('/api/v1') ? rawUrl : `${rawUrl.replace(/\/$/, '')}/api/v1`;

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  if (typeof window !== 'undefined') {
    const tokenStr = localStorage.getItem('auth-storage');
    if (tokenStr) {
      try {
        const tokenData = JSON.parse(tokenStr);
        if (tokenData.state && tokenData.state.token) {
          headers['Authorization'] = `Bearer ${tokenData.state.token}`;
        }
      } catch (e) { /* invalid JSON — ignore */ }
    }
  }
  const workspaceId = useGlobalStore.getState().currentWorkspaceId;
  if (workspaceId) {
    headers['X-Workspace-ID'] = workspaceId;
  }
  return headers;
}

async function parseErrorResponse(res: Response): Promise<string> {
  let errorMsg = `API error: ${res.status} ${res.statusText}`;
  try {
    const errorData = await res.json();
    if (errorData.detail) {
      if (typeof errorData.detail === 'string') {
        errorMsg = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        errorMsg = errorData.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
      } else {
        errorMsg = JSON.stringify(errorData.detail);
      }
    } else if (errorData.error && errorData.error.message) {
      errorMsg = errorData.error.message;
    } else {
      errorMsg = JSON.stringify(errorData);
    }
  } catch (e) { /* response body not JSON — use status text */ }
  return errorMsg;
}

class ApiClient {
  async get(endpoint: string) {
    const headers: Record<string, string> = { 'Content-Type': 'application/json', ...getAuthHeaders() };

    const res = await fetch(`${BASE_URL}${endpoint}`, { headers });
    if (!res.ok) {
      const errorMsg = await parseErrorResponse(res);
      throw new Error(errorMsg);
    }
    return await res.json();
  }

  async post(endpoint: string, body: any, customHeaders: Record<string, string> = {}) {
    const isFormData = body instanceof FormData;
    const reqHeaders: Record<string, string> = { ...customHeaders, ...getAuthHeaders() };
    if (!isFormData && !reqHeaders['Content-Type']) {
      reqHeaders['Content-Type'] = 'application/json';
    }

    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: reqHeaders,
      body: isFormData ? body : JSON.stringify(body),
    });
    if (!res.ok) {
      const errorMsg = await parseErrorResponse(res);
      throw new Error(errorMsg);
    }
    return await res.json();
  }

  async put(endpoint: string, body: any, customHeaders: Record<string, string> = {}) {
    const reqHeaders: Record<string, string> = { ...customHeaders, ...getAuthHeaders() };
    if (!reqHeaders['Content-Type']) {
      reqHeaders['Content-Type'] = 'application/json';
    }

    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method: 'PUT',
      headers: reqHeaders,
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const errorMsg = await parseErrorResponse(res);
      throw new Error(errorMsg);
    }
    return await res.json();
  }

  async download(endpoint: string, filename: string) {
    const headers: Record<string, string> = { ...getAuthHeaders() };

    const res = await fetch(`${BASE_URL}${endpoint}`, { headers });
    if (!res.ok) {
      const errorMsg = await parseErrorResponse(res);
      throw new Error(errorMsg);
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
  }

  async postDownload(endpoint: string, body: any, filename: string) {
    console.log(`[API POST DOWNLOAD Request]: ${BASE_URL}${endpoint}`);
    const workspaceId = useGlobalStore.getState().currentWorkspaceId;
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };

    if (typeof window !== 'undefined') {
      const tokenStr = localStorage.getItem('auth-storage');
      if (tokenStr) {
        try {
          const tokenData = JSON.parse(tokenStr);
          if (tokenData.state && tokenData.state.token) {
            headers['Authorization'] = `Bearer ${tokenData.state.token}`;
          }
        } catch (e) { }
      }
    }

    if (workspaceId) {
      headers['X-Workspace-ID'] = workspaceId;
    }

    try {
      const res = await fetch(`${BASE_URL}${endpoint}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      });
      console.log(`[API POST DOWNLOAD Response Status]: ${res.status} ${res.statusText}`);
      if (!res.ok) {
        let errorMsg = `API POST DOWNLOAD error: ${res.statusText}`;
        try {
          const text = await res.text();
          const errorData = JSON.parse(text);
          if (errorData.detail) {
            errorMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
          }
        } catch (e) { }
        throw new Error(errorMsg);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (e) {
      console.error(`[API POST DOWNLOAD Fetch Error]:`, e);
      throw e;
    }
  }
}

const api = new ApiClient();
export default api;
