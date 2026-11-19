import { useCallback, useEffect, useRef, useState } from 'react'

import { api as defaultApi, ApiError, NetworkError, type Api } from '../../api/client'
import type { Transaction } from '../../api/types'

/*
 * Safe confirmation state machine.
 *
 * - ONE idempotency key per quote, created when the quote is shown and reused for every retry.
 * - A second click while a request is in flight is ignored (ref guard, not just a disabled button).
 * - A timeout / lost response / in-progress / 5xx is NOT treated as failure: we query the original
 *   key until the backend reports COMPLETED or FAILED. We never submit with a new key.
 */

export type ConfirmState =
  | { kind: 'idle' }
  | { kind: 'submitting' }
  | { kind: 'checking'; attempt: number }
  | { kind: 'completed'; transaction: Transaction; recovered: boolean }
  | { kind: 'under_review'; transaction: Transaction } // outcome unconfirmed; Nium operations investigating
  | { kind: 'failed'; error: ApiError; transaction: Transaction | null } // conversion attempted, funds released
  | { kind: 'rejected'; error: ApiError } // nothing happened (expired quote, insufficient balance, ...)
  | { kind: 'not_received' } // backend has no record of the key: safe to retry with the SAME key
  | { kind: 'unresolved'; transactionId: string | null } // still unknown after polling

export interface ConfirmOptions {
  api?: Api
  pollIntervalMs?: number
  maxPolls?: number
  requestTimeoutMs?: number
}

export function newIdempotencyKey(): string {
  const c = globalThis.crypto
  const id = c && 'randomUUID' in c ? c.randomUUID() : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
  return `conv-${id}`
}

const UNCERTAIN_CODES = new Set(['RESPONSE_TIMEOUT', 'CONVERSION_IN_PROGRESS', 'CONVERSION_UNDER_REVIEW', 'INTERNAL_ERROR'])

export function isUncertain(err: unknown): boolean {
  if (err instanceof NetworkError) return true
  if (err instanceof ApiError) {
    return UNCERTAIN_CODES.has(err.code) || (err.status >= 500 && err.code.startsWith('HTTP_'))
  }
  return true // unknown error: do not assume failure
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export function useConfirmConversion(quoteId: string | null, options: ConfirmOptions = {}) {
  const { api = defaultApi, pollIntervalMs = 1000, maxPolls = 10, requestTimeoutMs = 15_000 } = options
  const [state, setState] = useState<ConfirmState>({ kind: 'idle' })
  const keyRef = useRef<{ quoteId: string | null; key: string }>({ quoteId: null, key: '' })
  const inFlight = useRef(false)
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  // Exactly one key per quote.
  if (keyRef.current.quoteId !== quoteId) {
    keyRef.current = { quoteId, key: newIdempotencyKey() }
  }

  useEffect(() => {
    setState({ kind: 'idle' })
  }, [quoteId])

  const update = (s: ConfirmState) => {
    if (mounted.current) setState(s)
  }

  const recover = useCallback(
    async (key: string) => {
      let lastWasNotFound = false
      let lastTxnId: string | null = null
      for (let attempt = 1; attempt <= maxPolls; attempt++) {
        update({ kind: 'checking', attempt })
        try {
          const txn = await api.getTransactionByKey(key)
          lastWasNotFound = false
          lastTxnId = txn.transaction_id
          if (txn.status === 'COMPLETED') return update({ kind: 'completed', transaction: txn, recovered: true })
          if (txn.status === 'REVIEW_REQUIRED') return update({ kind: 'under_review', transaction: txn })
          if (txn.status === 'FAILED') {
            return update({
              kind: 'failed',
              transaction: txn,
              error: new ApiError(500, 'CONVERSION_FAILED', txn.failure_message ?? 'The conversion failed.'),
            })
          }
        } catch (err) {
          lastWasNotFound = err instanceof ApiError && err.status === 404
        }
        if (attempt < maxPolls) await sleep(pollIntervalMs)
      }
      update(lastWasNotFound ? { kind: 'not_received' } : { kind: 'unresolved', transactionId: lastTxnId })
    },
    [api, maxPolls, pollIntervalMs],
  )

  const confirm = useCallback(async () => {
    if (!quoteId || inFlight.current) return // double-click guard
    inFlight.current = true
    const key = keyRef.current.key
    update({ kind: 'submitting' })
    try {
      const txn = await api.confirmQuote(quoteId, key, requestTimeoutMs)
      if (txn.status === 'REVIEW_REQUIRED') update({ kind: 'under_review', transaction: txn })
      else if (txn.status === 'COMPLETED') update({ kind: 'completed', transaction: txn, recovered: false })
      else await recover(key) // any other 2xx state: confirm via the original key, never assume
    } catch (err) {
      if (err instanceof ApiError && err.code === 'CONVERSION_FAILED') {
        const id = (err.details?.transaction_id as string | undefined) ?? null
        const txn = id ? await api.getTransaction(id).catch(() => null) : null
        update({ kind: 'failed', error: err, transaction: txn })
      } else if (isUncertain(err)) {
        await recover(key)
      } else {
        update({ kind: 'rejected', error: err as ApiError })
      }
    } finally {
      inFlight.current = false
    }
  }, [quoteId, api, requestTimeoutMs, recover])

  /** Re-check status for an unresolved conversion (same key). */
  const checkAgain = useCallback(async () => {
    if (inFlight.current) return
    inFlight.current = true
    try {
      await recover(keyRef.current.key)
    } finally {
      inFlight.current = false
    }
  }, [recover])

  return { state, confirm, checkAgain, idempotencyKey: keyRef.current.key }
}
