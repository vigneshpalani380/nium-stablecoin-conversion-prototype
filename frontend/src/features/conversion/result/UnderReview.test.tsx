import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../../api/client'
import { accountsUnderReview, completedTxn, config, fakeApi, reviewTxn } from '../../../test/fakeApi'
import { ConvertPage } from '../ConvertPage'
import { UNDER_REVIEW_MESSAGE } from './UnderReview'

async function confirmQuote(user: ReturnType<typeof userEvent.setup>) {
  await user.selectOptions(screen.getByLabelText('From'), 'acct-usd')
  await user.selectOptions(screen.getByLabelText('To'), 'acct-usdc-sol')
  await user.type(screen.getByLabelText(/Amount to convert/), '10000.00')
  await user.click(screen.getByRole('button', { name: 'Get quote' }))
  await user.click(await screen.findByRole('button', { name: 'Confirm conversion' }))
}

describe('Under review (ambiguous settlement outcome)', () => {
  it('shows the required message, details and unconfirmed credit, with no internal data', async () => {
    const user = userEvent.setup()
    const api = fakeApi({ confirmQuote: vi.fn().mockResolvedValue(reviewTxn) })
    render(<ConvertPage accounts={accountsUnderReview} config={config} onBalancesChanged={() => {}} api={api} />)
    await confirmQuote(user)

    expect(await screen.findByText('Status: Under review')).toBeInTheDocument()
    expect(screen.getByText(UNDER_REVIEW_MESSAGE)).toBeInTheDocument()
    expect(UNDER_REVIEW_MESSAGE).toBe(
      "We couldn't confirm the final settlement status of your conversion. Your funds remain reserved while our operations team investigates. You do not need to submit the conversion again. We'll notify you when the status is resolved.")
    expect(screen.getByText('txn-1')).toBeInTheDocument()
    expect(screen.getByText('not yet confirmed')).toBeInTheDocument()
    expect(screen.getByText(/account reserved total 10,000.00/)).toBeInTheDocument()
    expect(screen.getByText(/pending 9,950.00/)).toBeInTheDocument()
    expect(screen.getByText('Last updated')).toBeInTheDocument()
    const text = document.body.textContent ?? ''
    for (const internal of ['RVW-', 'NTF-', 'notification', 'OPERATIONS', 'reviewer', 'recovery']) {
      expect(text).not.toContain(internal)
    }
    // No resubmit / confirm action is offered while under review.
    expect(screen.queryByRole('button', { name: 'Confirm conversion' })).not.toBeInTheDocument()
    expect(api.confirmQuote).toHaveBeenCalledTimes(1)
  })

  it('a same-key retry answered CONVERSION_UNDER_REVIEW resolves to Under review via the original key', async () => {
    const user = userEvent.setup()
    const api = fakeApi({
      confirmQuote: vi.fn().mockRejectedValue(new ApiError(409, 'CONVERSION_UNDER_REVIEW', 'under review', true)),
      getTransactionByKey: vi.fn().mockResolvedValue(reviewTxn),
    })
    render(<ConvertPage accounts={accountsUnderReview} config={config} onBalancesChanged={() => {}} api={api}
      confirmOptions={{ pollIntervalMs: 1, maxPolls: 2 }} />)
    await confirmQuote(user)
    expect(await screen.findByText('Status: Under review')).toBeInTheDocument()
  })

  it('Refresh status shows the authoritative outcome once operations resolve it', async () => {
    const user = userEvent.setup()
    const api = fakeApi({
      confirmQuote: vi.fn().mockResolvedValue(reviewTxn),
      getTransactionByKey: vi.fn().mockResolvedValue(completedTxn),
    })
    render(<ConvertPage accounts={accountsUnderReview} config={config} onBalancesChanged={() => {}} api={api} />)
    await confirmQuote(user)
    await user.click(await screen.findByRole('button', { name: 'Refresh status' }))
    expect(await screen.findByText(/Conversion completed/)).toBeInTheDocument()
    expect(api.confirmQuote).toHaveBeenCalledTimes(1)
  })
})
