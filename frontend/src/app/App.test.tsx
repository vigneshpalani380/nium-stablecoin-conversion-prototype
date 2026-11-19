import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'

import { fakeApi } from '../test/fakeApi'
import App from './App'

it('renders wallet shell with network-labelled balances and tabs', async () => {
  render(<App api={fakeApi()} />)
  expect(screen.getByRole('heading', { name: 'Wallet' })).toBeInTheDocument()
  expect(screen.getByText('Nium Wallet Prototype')).toBeInTheDocument()
  const sol = await screen.findByRole('article', { name: 'USDC-Solana balance' })
  expect(within(sol).getByText('Solana')).toBeInTheDocument()
  expect(within(sol).getByText(/5,000\.00/)).toBeInTheDocument()
  expect(screen.getByRole('article', { name: 'USDC-Base balance' })).toBeInTheDocument()
  expect(within(screen.getByRole('article', { name: 'USD balance' })).getByText('Fiat')).toBeInTheDocument()
})

it('activity tab lists conversions', async () => {
  const user = userEvent.setup()
  render(<App api={fakeApi()} />)
  await screen.findByRole('article', { name: 'USD balance' })
  await user.click(screen.getByRole('button', { name: 'Activity' }))
  expect(await screen.findByText('Recent conversions')).toBeInTheDocument()
  expect(screen.getByText('txn-1')).toBeInTheDocument()
  await user.click(screen.getByText('txn-1'))
  expect(screen.getByText('Transaction detail')).toBeInTheDocument()
})
