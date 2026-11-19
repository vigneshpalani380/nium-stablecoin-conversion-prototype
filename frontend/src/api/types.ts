// API shapes. All money values are decimal strings; the UI never does float arithmetic on them.

export interface Account {
  id: string
  asset_code: string
  asset_type: 'FIAT' | 'STABLECOIN'
  network: string | null
  display_name: string
  precision: number
  available_balance: string
  reserved_balance: string
  pending_balance: string
  status: string
}

export interface PairOption {
  source_account_id: string
  destination_account_id: string
  source_display_name: string
  destination_display_name: string
}

export interface ConversionConfig {
  customer_id: string
  fee_rate: string
  fee_currency_mode: string
  quote_ttl_seconds: number
  rate_source: string
  rounding: string
  assets: { account_id: string; asset_code: string; network: string | null; display_name: string; precision: number }[]
  pairs: PairOption[]
  demo_mode: boolean
}

export interface Party {
  account_id: string
  asset_code: string
  network: string | null
  display_name: string
}

export interface Quote {
  quote_id: string
  status: 'OPEN' | 'CONFIRMED' | 'EXPIRED' | 'CANCELLED'
  rate_source: string
  source: Party
  destination: Party
  gross_source_amount: string
  fee_rate: string
  fee_amount: string
  fee_currency: string
  net_source_amount: string
  exchange_rate: string
  destination_amount: string
  created_at: string
  expires_at: string
  seconds_remaining: number
}

export interface BalanceTriple {
  available: string
  reserved: string
  pending: string
}

export interface Transaction {
  transaction_id: string
  reference: string
  status: 'RESERVED' | 'COMPLETED' | 'FAILED' | 'REVIEW_REQUIRED'
  quote_id: string
  idempotency_key: string
  source: Party
  destination: Party
  gross_source_amount: string
  fee_rate: string
  fee_amount: string
  fee_currency: string
  net_source_amount: string
  exchange_rate: string
  rate_source: string
  destination_amount: string
  balances: {
    source: { before: BalanceTriple | null; after: BalanceTriple | null }
    destination: { before: BalanceTriple | null; after: BalanceTriple | null }
  }
  failure_code: string | null
  failure_message: string | null
  created_at: string
  reserved_at: string
  settled_at: string | null
  released_at: string | null
  last_updated_at: string
}

export interface DemoFaults {
  pause_after_reserve_seconds: number
  fail_mid_reserve: boolean
  fail_mid_settle: boolean
  timeout_after_commit: boolean
  uncertain_commit: 'COMMITTED' | 'ROLLED_BACK' | null
  recovery_lookup_fails: boolean
}
