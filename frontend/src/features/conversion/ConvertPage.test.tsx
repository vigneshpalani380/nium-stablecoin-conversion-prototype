import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ApiError, NetworkError } from '../../api/client'
import { accounts, completedTxn, config, fakeApi } from '../../test/fakeApi'
import { ConvertPage } from './ConvertPage'

async function fillAndQuote(user: ReturnType<typeof userEvent.setup>) {
  await user.selectOptions(screen.getByLabelText('From'), 'acct-usd')
  await user.selectOptions(screen.getByLabelText('To'), 'acct-usdc-sol')
  await user.type(screen.getByLabelText(/Amount to convert/), '10000.00')
  await user.click(screen.getByRole('button', { name: 'Get quote' }))
  await screen.findByText('Review conversion')
}

describe('ConvertPage', () => {
  it('destination options are limited to enabled pairs (no USDC-Base)', async () => {
    const user = userEvent.setup()
    render(<ConvertPage accounts={accounts} config={config} onBalancesChanged={() => {}} api={fakeApi()} />)
    expect(screen.getByLabelText('From').querySelectorAll('option')).toHaveLength(4) // placeholder + 3 sources
    await user.selectOptions(screen.getByLabelText('From'), 'acct-usd')
    const dests = Array.from(screen.getByLabelText('To').querySelectorAll('option')).map((o) => o.textContent)
    expect(dests).toEqual(['Select destination account', 'USDC-Solana'])
  })

  it('shows quote breakdown with simulated label, and a fast double click confirms once', async () => {
    const user = userEvent.setup()
    let resolve!: (v: unknown) => void
    const api = fakeApi({ confirmQuote: vi.fn(() => new Promise((r) => (resolve = r))) })
    render(<ConvertPage accounts={accounts} config={config} onBalancesChanged={() => {}} api={api} />)
    await fillAndQuote(user)
    expect(screen.getByText('Simulated demo rate')).toBeInTheDocument()
    expect(screen.getByText('− 50.00 USD')).toBeInTheDocument()
    expect(screen.getByText('9,950.00 USDC')).toBeInTheDocument()

    const btn = screen.getByRole('button', { name: 'Confirm conversion' })
    await user.dblClick(btn)
    await user.click(btn)
    resolve(completedTxn)
    await screen.findByText(/Conversion completed/)
    expect(api.confirmQuote).toHaveBeenCalledTimes(1)
    expect(screen.getByText('txn-1')).toBeInTheDocument()
  })

  it('on a lost response shows "Checking conversion status…" then the original result', async () => {
    const user = userEvent.setup()
    let release!: (v: unknown) => void
    const api = fakeApi({
      confirmQuote: vi.fn().mockRejectedValue(new NetworkError(true)),
      getTransactionByKey: vi.fn(() => new Promise((r) => (release = r))),
    })
    render(<ConvertPage accounts={accounts} config={config} onBalancesChanged={() => {}} api={api}
      confirmOptions={{ pollIntervalMs: 1, maxPolls: 2 }} />)
    await fillAndQuote(user)
    await user.click(screen.getByRole('button', { name: 'Confirm conversion' }))
    expect(await screen.findByText('Checking conversion status…')).toBeInTheDocument()
    release(completedTxn)
    expect(await screen.findByText(/nothing was submitted twice/)).toBeInTheDocument()
    expect(api.confirmQuote).toHaveBeenCalledTimes(1)
  })

  it('expired quote shows actionable message and offers a new quote', async () => {
    const user = userEvent.setup()
    const api = fakeApi({ confirmQuote: vi.fn().mockRejectedValue(new ApiError(409, 'QUOTE_EXPIRED', 'This quote has expired. Request a new quote.', true)) })
    render(<ConvertPage accounts={accounts} config={config} onBalancesChanged={() => {}} api={api} />)
    await fillAndQuote(user)
    await user.click(screen.getByRole('button', { name: 'Confirm conversion' }))
    expect(await screen.findByText('Quote expired')).toBeInTheDocument()
    expect(screen.getByText(/No funds were moved/)).toBeInTheDocument()
  })

  it('changing inputs discards the current quote', async () => {
    const user = userEvent.setup()
    const api = fakeApi()
    render(<ConvertPage accounts={accounts} config={config} onBalancesChanged={() => {}} api={api} />)
    await fillAndQuote(user)
    await user.type(screen.getByLabelText(/Amount to convert/), '1')
    await waitFor(() => expect(screen.queryByText('Review conversion')).not.toBeInTheDocument())
    expect(api.cancelQuote).toHaveBeenCalledWith('q-1')
  })

  it('blocks invalid amounts before requesting a quote', async () => {
    const user = userEvent.setup()
    render(<ConvertPage accounts={accounts} config={config} onBalancesChanged={() => {}} api={fakeApi()} />)
    await user.selectOptions(screen.getByLabelText('From'), 'acct-usd')
    await user.selectOptions(screen.getByLabelText('To'), 'acct-usdc-sol')
    await user.type(screen.getByLabelText(/Amount to convert/), '1.001')
    expect(screen.getByText('This asset supports at most 2 decimal places.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Get quote' })).toBeDisabled()
  })
})
