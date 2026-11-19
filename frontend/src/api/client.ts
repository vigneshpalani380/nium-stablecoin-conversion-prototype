import type { Account, ConversionConfig, DemoFaults, Quote, Transaction } from './types'

/** Error returned by the backend in the standard envelope. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly retryable: boolean = false,
    public readonly details: Record<string, unknown> = {},
    public readonly requestId: string | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** The request never produced an HTTP response (offline, aborted, timed out). Outcome unknown. */
export class NetworkError extends Error {
  constructor(public readonly timedOut: boolean) {
    super(timedOut ? 'The request timed out.' : 'The network request failed.')
    this.name = 'NetworkError'
  }
}

const DEFAULT_TIMEOUT_MS = 15_000

async function request<T>(path: string, init: RequestInit = {}, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)
  let res: Response
  try {
    res = await fetch(path, {
      ...init,
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
    })
  } catch {
    throw new NetworkError(timedOut)
  } finally {
    clearTimeout(timer)
  }
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const err = body?.error
    throw new ApiError(
      res.status,
      err?.code ?? `HTTP_${res.status}`,
      err?.message ?? `Request failed with status ${res.status}.`,
      err?.retryable ?? res.status >= 500,
      err?.details ?? {},
      err?.request_id ?? res.headers.get('X-Request-ID'),
    )
  }
  return body as T
}

export const api = {
  getAccounts: () => request<{ customer_id: string; accounts: Account[] }>('/api/v1/accounts').then((r) => r.accounts),
  getConfig: () => request<ConversionConfig>('/api/v1/conversion/config'),
  createQuote: (source_account_id: string, destination_account_id: string, gross_source_amount: string) =>
    request<Quote>('/api/v1/conversion/quotes', {
      method: 'POST',
      body: JSON.stringify({ source_account_id, destination_account_id, gross_source_amount }),
    }),
  cancelQuote: (quoteId: string) =>
    request<Quote>(`/api/v1/conversion/quotes/${encodeURIComponent(quoteId)}/cancel`, { method: 'POST' }),
  /** Financial values come from the persisted quote server-side; only the quote id and key are sent. */
  confirmQuote: (quoteId: string, idempotencyKey: string, timeoutMs?: number) =>
    request<Transaction>(
      `/api/v1/conversion/quotes/${encodeURIComponent(quoteId)}/confirm`,
      { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey } },
      timeoutMs,
    ),
  getTransactionByKey: (idempotencyKey: string) =>
    request<Transaction>(`/api/v1/conversion/transactions/by-idempotency-key/${encodeURIComponent(idempotencyKey)}`),
  getTransaction: (id: string) => request<Transaction>(`/api/v1/conversion/transactions/${encodeURIComponent(id)}`),
  listTransactions: () =>
    request<{ transactions: Transaction[] }>('/api/v1/conversion/transactions').then((r) => r.transactions),
  demo: {
    getFaults: () => request<DemoFaults>('/api/v1/demo/faults'),
    setFaults: (faults: Partial<Omit<DemoFaults, 'uncertain_commit'>> & { uncertain_commit?: 'OFF' | 'COMMITTED' | 'ROLLED_BACK' }) =>
      request<DemoFaults>('/api/v1/demo/faults', { method: 'PUT', body: JSON.stringify(faults) }),
    expireQuote: (quoteId: string) =>
      request<{ expired: boolean }>(`/api/v1/demo/quotes/${encodeURIComponent(quoteId)}/expire`, { method: 'POST' }),
    reset: () => request<{ reset: boolean }>('/api/v1/demo/reset', { method: 'POST' }),
  },
}

export type Api = typeof api
