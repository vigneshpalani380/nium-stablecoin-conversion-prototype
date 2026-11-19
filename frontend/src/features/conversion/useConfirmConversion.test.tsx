import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ApiError, NetworkError } from '../../api/client'
import { completedTxn, fakeApi } from '../../test/fakeApi'
import { useConfirmConversion } from './useConfirmConversion'

const opts = { pollIntervalMs: 1, maxPolls: 3 }

function setup(apiOverrides = {}) {
  const api = fakeApi(apiOverrides)
  const hook = renderHook(({ quoteId }) => useConfirmConversion(quoteId, { api, ...opts }), {
    initialProps: { quoteId: 'q-1' as string | null },
  })
  return { api, hook }
}

describe('useConfirmConversion', () => {
  it('ignores a rapid double click: only one confirm request is sent', async () => {
    let resolve!: (v: unknown) => void
    const { api, hook } = setup({ confirmQuote: vi.fn(() => new Promise((r) => (resolve = r))) })
    act(() => {
      void hook.result.current.confirm()
      void hook.result.current.confirm()
      void hook.result.current.confirm()
    })
    await act(async () => resolve(completedTxn))
    expect(api.confirmQuote).toHaveBeenCalledTimes(1)
    expect(hook.result.current.state.kind).toBe('completed')
  })

  it('on timeout, recovers by querying the ORIGINAL key and never sends a new confirm', async () => {
    const { api, hook } = setup({ confirmQuote: vi.fn().mockRejectedValue(new NetworkError(true)) })
    const key = hook.result.current.idempotencyKey
    await act(() => hook.result.current.confirm())
    await waitFor(() => expect(hook.result.current.state.kind).toBe('completed'))
    expect(api.confirmQuote).toHaveBeenCalledTimes(1)
    expect(api.confirmQuote).toHaveBeenCalledWith('q-1', key, expect.any(Number))
    expect(api.getTransactionByKey).toHaveBeenCalledWith(key)
    const s = hook.result.current.state
    expect(s.kind === 'completed' && s.recovered).toBe(true)
  })

  it('treats a simulated 504 RESPONSE_TIMEOUT and CONVERSION_IN_PROGRESS as uncertain, not failed', async () => {
    for (const code of ['RESPONSE_TIMEOUT', 'CONVERSION_IN_PROGRESS']) {
      const { api, hook } = setup({ confirmQuote: vi.fn().mockRejectedValue(new ApiError(code === 'RESPONSE_TIMEOUT' ? 504 : 409, code, 'x', true)) })
      await act(() => hook.result.current.confirm())
      await waitFor(() => expect(hook.result.current.state.kind).toBe('completed'))
      expect(api.getTransactionByKey).toHaveBeenCalledWith(hook.result.current.idempotencyKey)
    }
  })

  it('keeps polling while the transaction is RESERVED', async () => {
    const getTransactionByKey = vi.fn()
      .mockResolvedValueOnce({ ...completedTxn, status: 'RESERVED' })
      .mockResolvedValueOnce(completedTxn)
    const { hook } = setup({ confirmQuote: vi.fn().mockRejectedValue(new NetworkError(true)), getTransactionByKey })
    await act(() => hook.result.current.confirm())
    await waitFor(() => expect(hook.result.current.state.kind).toBe('completed'))
    expect(getTransactionByKey).toHaveBeenCalledTimes(2)
  })

  it('reports not_received when the server has no record; retry reuses the same key', async () => {
    const confirmQuote = vi.fn().mockRejectedValueOnce(new NetworkError(false)).mockResolvedValueOnce(completedTxn)
    const getTransactionByKey = vi.fn().mockRejectedValue(new ApiError(404, 'TRANSACTION_NOT_FOUND', 'none'))
    const { hook } = setup({ confirmQuote, getTransactionByKey })
    const key = hook.result.current.idempotencyKey
    await act(() => hook.result.current.confirm())
    await waitFor(() => expect(hook.result.current.state.kind).toBe('not_received'))
    await act(() => hook.result.current.confirm())
    expect(confirmQuote).toHaveBeenCalledTimes(2)
    expect(confirmQuote.mock.calls[0][1]).toBe(key)
    expect(confirmQuote.mock.calls[1][1]).toBe(key)
  })

  it('reports unresolved (not failed) if status cannot be determined', async () => {
    const { hook } = setup({
      confirmQuote: vi.fn().mockRejectedValue(new NetworkError(true)),
      getTransactionByKey: vi.fn().mockRejectedValue(new NetworkError(false)),
    })
    await act(() => hook.result.current.confirm())
    await waitFor(() => expect(hook.result.current.state.kind).toBe('unresolved'))
  })

  it('QUOTE_EXPIRED is a definite rejection (no recovery polling)', async () => {
    const { api, hook } = setup({ confirmQuote: vi.fn().mockRejectedValue(new ApiError(409, 'QUOTE_EXPIRED', 'expired', true)) })
    await act(() => hook.result.current.confirm())
    expect(hook.result.current.state.kind).toBe('rejected')
    expect(api.getTransactionByKey).not.toHaveBeenCalled()
  })

  it('CONVERSION_FAILED shows failure with released funds', async () => {
    const { hook } = setup({
      confirmQuote: vi.fn().mockRejectedValue(new ApiError(500, 'CONVERSION_FAILED', 'released', false, { transaction_id: 'txn-1' })),
      getTransaction: vi.fn().mockResolvedValue({ ...completedTxn, status: 'FAILED' }),
    })
    await act(() => hook.result.current.confirm())
    expect(hook.result.current.state.kind).toBe('failed')
  })

  it('generates a new key only when the quote changes', () => {
    const { hook } = setup()
    const k1 = hook.result.current.idempotencyKey
    hook.rerender({ quoteId: 'q-1' })
    expect(hook.result.current.idempotencyKey).toBe(k1)
    hook.rerender({ quoteId: 'q-2' })
    expect(hook.result.current.idempotencyKey).not.toBe(k1)
  })
})
