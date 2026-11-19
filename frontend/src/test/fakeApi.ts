import { vi } from 'vitest'

import type { Api } from '../api/client'
import type { Account, ConversionConfig, Quote, Transaction } from '../api/types'

export const accounts: Account[] = [
  { id: 'acct-usd', asset_code: 'USD', asset_type: 'FIAT', network: null, display_name: 'USD', precision: 2,
    available_balance: '25000.00', reserved_balance: '0.00', pending_balance: '0.00', status: 'ACTIVE' },
  { id: 'acct-inr', asset_code: 'INR', asset_type: 'FIAT', network: null, display_name: 'INR', precision: 2,
    available_balance: '2000000.00', reserved_balance: '0.00', pending_balance: '0.00', status: 'ACTIVE' },
  { id: 'acct-usdc-sol', asset_code: 'USDC', asset_type: 'STABLECOIN', network: 'SOLANA', display_name: 'USDC-Solana',
    precision: 6, available_balance: '5000.000000', reserved_balance: '0.000000', pending_balance: '0.000000', status: 'ACTIVE' },
  { id: 'acct-usdc-base', asset_code: 'USDC', asset_type: 'STABLECOIN', network: 'BASE', display_name: 'USDC-Base',
    precision: 6, available_balance: '1000.000000', reserved_balance: '0.000000', pending_balance: '0.000000', status: 'ACTIVE' },
]

export const config: ConversionConfig = {
  customer_id: 'cust-demo-marketplace', fee_rate: '0.005', fee_currency_mode: 'SOURCE', quote_ttl_seconds: 30,
  rate_source: 'SIMULATED', rounding: 'ROUND_HALF_UP', demo_mode: false,
  assets: [],
  pairs: [
    { source_account_id: 'acct-usdc-sol', destination_account_id: 'acct-usd', source_display_name: 'USDC-Solana', destination_display_name: 'USD' },
    { source_account_id: 'acct-usd', destination_account_id: 'acct-usdc-sol', source_display_name: 'USD', destination_display_name: 'USDC-Solana' },
    { source_account_id: 'acct-usdc-sol', destination_account_id: 'acct-inr', source_display_name: 'USDC-Solana', destination_display_name: 'INR' },
    { source_account_id: 'acct-inr', destination_account_id: 'acct-usdc-sol', source_display_name: 'INR', destination_display_name: 'USDC-Solana' },
  ],
}

const usd = { account_id: 'acct-usd', asset_code: 'USD', network: null, display_name: 'USD' }
const usdc = { account_id: 'acct-usdc-sol', asset_code: 'USDC', network: 'SOLANA', display_name: 'USDC-Solana' }

export const quote: Quote = {
  quote_id: 'q-1', status: 'OPEN', rate_source: 'SIMULATED', source: usd, destination: usdc,
  gross_source_amount: '10000.00', fee_rate: '0.005', fee_amount: '50.00', fee_currency: 'USD',
  net_source_amount: '9950.00', exchange_rate: '1.0000', destination_amount: '9950.000000',
  created_at: '2026-01-01T12:00:00.000Z', expires_at: '2026-01-01T12:00:30.000Z', seconds_remaining: 30,
}

export const completedTxn: Transaction = {
  transaction_id: 'txn-1', reference: 'txn-1', status: 'COMPLETED', quote_id: 'q-1', idempotency_key: 'conv-x',
  source: usd, destination: usdc, gross_source_amount: '10000.00', fee_rate: '0.005', fee_amount: '50.00',
  fee_currency: 'USD', net_source_amount: '9950.00', exchange_rate: '1.0000', rate_source: 'SIMULATED',
  destination_amount: '9950.000000',
  balances: {
    source: { before: { available: '25000.00', reserved: '0.00', pending: '0.00' }, after: { available: '15000.00', reserved: '0.00', pending: '0.00' } },
    destination: { before: { available: '5000.000000', reserved: '0.000000', pending: '0.000000' }, after: { available: '14950.000000', reserved: '0.000000', pending: '0.000000' } },
  },
  failure_code: null, failure_message: null, created_at: '2026-01-01T12:00:05.000Z',
  reserved_at: '2026-01-01T12:00:05.000Z', settled_at: '2026-01-01T12:00:05.000Z', released_at: null,
  last_updated_at: '2026-01-01T12:00:05.000Z',
}

export function fakeApi(overrides: Partial<Api> = {}): Api {
  return {
    getAccounts: vi.fn().mockResolvedValue(accounts),
    getConfig: vi.fn().mockResolvedValue(config),
    createQuote: vi.fn().mockResolvedValue(quote),
    cancelQuote: vi.fn().mockResolvedValue({ ...quote, status: 'CANCELLED' }),
    confirmQuote: vi.fn().mockResolvedValue(completedTxn),
    getTransactionByKey: vi.fn().mockResolvedValue(completedTxn),
    getTransaction: vi.fn().mockResolvedValue(completedTxn),
    listTransactions: vi.fn().mockResolvedValue([completedTxn]),
    demo: {
      getFaults: vi.fn().mockResolvedValue({ pause_after_reserve_seconds: 0, fail_mid_reserve: false, fail_mid_settle: false, timeout_after_commit: false }),
      setFaults: vi.fn(),
      expireQuote: vi.fn().mockResolvedValue({ expired: true }),
      reset: vi.fn().mockResolvedValue({ reset: true }),
    },
    ...overrides,
  } as Api
}

export const reviewTxn: Transaction = {
  ...completedTxn,
  status: 'REVIEW_REQUIRED',
  settled_at: null,
  balances: {
    source: { before: completedTxn.balances.source.before, after: null },
    destination: { before: completedTxn.balances.destination.before, after: null },
  },
  last_updated_at: '2026-01-01T12:00:06.000Z',
}

export const accountsUnderReview: Account[] = accounts.map((a) =>
  a.id === 'acct-usd' ? { ...a, available_balance: '15000.00', reserved_balance: '10000.00' }
    : a.id === 'acct-usdc-sol' ? { ...a, pending_balance: '9950.000000' } : a)
