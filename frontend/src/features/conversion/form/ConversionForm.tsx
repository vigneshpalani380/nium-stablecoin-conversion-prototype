import { useMemo } from 'react'

import type { Account, ConversionConfig } from '../../../api/types'
import { formatAmount, formatPercent } from '../../../components/ui/format'
import { validateAmount } from './amount'

export interface FormValues {
  sourceId: string
  destinationId: string
  amount: string
}

interface Props {
  accounts: Account[]
  config: ConversionConfig
  values: FormValues
  onChange: (values: FormValues) => void
  onSubmit: () => void
  busy: boolean
  disabled?: boolean
}

/** Source/destination selectors are driven entirely by the enabled pairs from the config API. */
export function ConversionForm({ accounts, config, values, onChange, onSubmit, busy, disabled }: Props) {
  const byId = useMemo(() => new Map(accounts.map((a) => [a.id, a])), [accounts])
  const sources = useMemo(() => {
    const ids = new Set(config.pairs.map((p) => p.source_account_id))
    return accounts.filter((a) => ids.has(a.id))
  }, [accounts, config.pairs])
  const destinations = useMemo(
    () =>
      config.pairs
        .filter((p) => p.source_account_id === values.sourceId)
        .map((p) => byId.get(p.destination_account_id))
        .filter((a): a is Account => !!a),
    [config.pairs, values.sourceId, byId],
  )

  const source = byId.get(values.sourceId)
  const amountError = values.amount && source ? validateAmount(values.amount, source.precision, source.available_balance) : null
  const canSubmit =
    !!source && !!values.destinationId && values.amount.trim() !== '' && !amountError && !busy && !disabled

  const setSource = (sourceId: string) => {
    const stillValid = config.pairs.some((p) => p.source_account_id === sourceId && p.destination_account_id === values.destinationId)
    onChange({ ...values, sourceId, destinationId: stillValid ? values.destinationId : '' })
  }

  return (
    <form
      className="card"
      aria-labelledby="convert-heading"
      onSubmit={(e) => {
        e.preventDefault()
        if (canSubmit) onSubmit()
      }}
    >
      <h2 id="convert-heading">Convert</h2>
      <div className="form-grid">
        <div className="field">
          <label htmlFor="source">From</label>
          <select id="source" value={values.sourceId} onChange={(e) => setSource(e.target.value)} disabled={disabled}>
            <option value="">Select source account</option>
            {sources.map((a) => (
              <option key={a.id} value={a.id}>
                {a.display_name}
              </option>
            ))}
          </select>
          <span className="hint num">
            {source ? `Available: ${formatAmount(source.available_balance)} ${source.asset_code}` : ' '}
          </span>
        </div>
        <div className="field">
          <label htmlFor="destination">To</label>
          <select
            id="destination"
            value={values.destinationId}
            onChange={(e) => onChange({ ...values, destinationId: e.target.value })}
            disabled={disabled || !values.sourceId}
          >
            <option value="">{values.sourceId ? 'Select destination account' : 'Choose a source first'}</option>
            {destinations.map((a) => (
              <option key={a.id} value={a.id}>
                {a.display_name}
              </option>
            ))}
          </select>
          <span className="hint">Only enabled conversion pairs are listed.</span>
        </div>
        <div className="field">
          <label htmlFor="amount">Amount to convert{source ? ` (${source.asset_code})` : ''}</label>
          <input
            id="amount"
            inputMode="decimal"
            autoComplete="off"
            placeholder="0.00"
            value={values.amount}
            onChange={(e) => onChange({ ...values, amount: e.target.value })}
            aria-invalid={amountError ? 'true' : 'false'}
            aria-describedby="amount-help"
            disabled={disabled}
          />
          <span id="amount-help" className="hint" role={amountError ? 'alert' : undefined} style={amountError ? { color: 'var(--color-error)' } : undefined}>
            {amountError ?? `Gross amount; a ${formatPercent(config.fee_rate)} fee is deducted from it.`}
          </span>
        </div>
      </div>
      <div className="actions">
        <button type="submit" className="btn btn-primary" disabled={!canSubmit}>
          {busy ? 'Getting quote…' : 'Get quote'}
        </button>
      </div>
    </form>
  )
}

