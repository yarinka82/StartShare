
import axios from 'axios';

axios.defaults.withCredentials = true;
axios.defaults.xsrfCookieName = 'csrftoken';
axios.defaults.xsrfHeaderName = 'X-CSRFToken';

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}

const UNSAFE_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE'];

export async function apiFetch(url: string, options: RequestInit = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const headers = new Headers(options.headers || {});

  if (UNSAFE_METHODS.includes(method)) {
    const csrfToken = getCookie('csrftoken');
    if (csrfToken) headers.set('X-CSRFToken', csrfToken);
  }
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  return fetch(url, {
    ...options,
    method,
    headers,
    credentials: 'include',
  });
}

// Единая обработка ответа: бросает осмысленную ошибку на не-ok,
// безопасно обрабатывает пустое тело (204 No Content и подобные).
async function handleResponse(response: Response) {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const text = await response.text();
      if (text) detail = text;
    } catch {
      // тело недоступно — оставляем statusText
    }
    throw new Error(`Request failed: ${response.status} ${detail}`);
  }

  if (response.status === 204) {
    return null;
  }

  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

// Для совместимости с axios интерцепторами (если нужны)
export const apiClient = {
  get: async (url: string) => {
    const response = await apiFetch(url);
    return handleResponse(response);
  },
  post: async (url: string, data: any) => {
    const response = await apiFetch(url, {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },
  patch: async (url: string, data: any) => {
    const response = await apiFetch(url, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },
  delete: async (url: string) => {
    const response = await apiFetch(url, {
      method: 'DELETE',
    });
    return handleResponse(response);
  },
};

export default apiClient;