import type { Card, CardInput, CardPage, Category } from './types'

const BASE = '/api'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(BASE + path, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    })
  } catch {
    throw new ApiError(0, '无法连接后端服务，请确认后端已启动')
  }

  if (res.status === 204) return undefined as T

  const text = await res.text()
  let body: unknown = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = text
    }
  }

  if (!res.ok) {
    throw new ApiError(res.status, extractDetail(body, res.status))
  }
  return body as T
}

function extractDetail(body: unknown, status: number): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: string } | undefined
      if (first?.msg) return first.msg.replace(/^Value error, /, '')
    }
  }
  // A 5xx without a JSON body means the request never reached our API — in dev
  // the Vite proxy answers 500 with plain text when the backend is not running.
  if (status >= 500) {
    return '无法连接后端服务，请确认后端已启动，或端口是否一致'
  }
  return `请求失败（HTTP ${status}）`
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    search.set(key, String(value))
  }
  const s = search.toString()
  return s ? `?${s}` : ''
}

export const api = {
  listCategories: () => request<Category[]>('/categories'),

  createCategory: (name: string) =>
    request<Category>('/categories', {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),

  renameCategory: (id: number, name: string) =>
    request<Category>(`/categories/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ name }),
    }),

  deleteCategory: (id: number) =>
    request<void>(`/categories/${id}`, { method: 'DELETE' }),

  listCards: (params: {
    categoryId?: number | 'all'
    keyword?: string
    page?: number
    pageSize?: number
  }) =>
    request<CardPage>(
      '/cards' +
        qs({
          category_id:
            params.categoryId === undefined || params.categoryId === 'all'
              ? undefined
              : params.categoryId,
          keyword: params.keyword?.trim() || undefined,
          page: params.page,
          page_size: params.pageSize,
        }),
    ),

  createCard: (payload: CardInput) =>
    request<Card>('/cards', { method: 'POST', body: JSON.stringify(payload) }),

  getCard: (id: number) => request<Card>(`/cards/${id}`),

  updateCard: (id: number, payload: Partial<CardInput>) =>
    request<Card>(`/cards/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),

  deleteCard: (id: number) => request<void>(`/cards/${id}`, { method: 'DELETE' }),

  /** Re-insert a deleted card snapshot (undo). Keeps id + review_count. */
  restoreCard: (payload: {
    id?: number
    question: string
    answer: string
    category_id: number
    review_count?: number
  }) => request<Card>('/cards/restore', { method: 'POST', body: JSON.stringify(payload) }),

  randomCard: (categoryId?: number | 'all') =>
    request<Card | null>(
      '/review/random' +
        qs({
          category_id:
            categoryId === undefined || categoryId === 'all' ? undefined : categoryId,
        }),
    ),

  markReviewed: (id: number) =>
    request<Card>(`/cards/${id}/reviewed`, { method: 'POST' }),
}
