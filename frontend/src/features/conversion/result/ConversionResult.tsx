import type { BalanceTriple, Transaction } from '../../../api/types'
import { formatAmount, formatDateTime } from '../../../components/ui/format'
import { StatusBadge } from '../../../components/ui/StatusBadge'

export function BalanceChange({
  label,
  asset,
  before,
  after,
}: {
  label: string
  asset: string
  before: BalanceTriple | null
  after: BalanceTriple | null
}) {
  return (
    <div>
      <div style={{ fontWeight: 600 }}>{label}</div>
      <table className="data" aria-label={`${label} balance change`}>
        <thead>
          <tr>
            <th scope="col">Balance</th>
            <th scope="col" className="num">Before</th>
            <th scope="col" className="num">After</th>
          </tr>
        </thead>
        <tbody>
          {(['available', 'reserved', 'pending'] as const).map((k) => (
            <tr key={k} style={{ cursor: 'default' }}>
              <th scope="row" style={{ fontWeight: 400, textTransform: 'capitalize' }}>{k}</th>
              <td className="num">{before ? `${formatAmount(before[k])} ${asset}` : '—'}</td>
              <td className="num">{after ? `${formatAmount(after[k])} ${asset}` : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function ConversionResult({ transaction, recovered, onNew }: { transaction: Transaction; recovered: boolean; onNew: () => void }) {
  const t = transaction
  return (
    <section className="card" aria-labelledby="result-heading">
      <h2 id="result-heading">
        Conversion {t.status === 'COMPLETED' ? 'completed' : 'status'} <StatusBadge status={t.status} />
      </h2>
      {recovered && (
        <p className="muted">
          The original response was lost, so we checked the status using your original reference. This is the
          original conversion; nothing was submitted twice.
        </p>
      )}
      <dl className="summary">
        <dt>Converted</dt>
        <dd>{formatAmount(t.gross_source_amount)} {t.source.display_name}</dd>
        <dt>Fee</dt>
        <dd>{formatAmount(t.fee_amount)} {t.fee_currency}</dd>
        <dt>Rate (simulated)</dt>
        <dd>1 {t.source.asset_code} = {t.exchange_rate} {t.destination.asset_code}</dd>
        <div className="total" style={{ display: 'contents' }}>
          <dt>Received</dt>
          <dd>{formatAmount(t.destination_amount)} {t.destination.display_name}</dd>
        </div>
      </dl>
      <p className="muted" style={{ marginTop: 'var(--space-3)' }}>
        Reference <span className="mono">{t.reference}</span> · {formatDateTime(t.settled_at ?? t.created_at)}
      </p>
      <div className="snapshot-grid">
        <BalanceChange label={t.source.display_name} asset={t.source.asset_code} {...t.balances.source} />
        <BalanceChange label={t.destination.display_name} asset={t.destination.asset_code} {...t.balances.destination} />
      </div>
      <div className="actions">
        <button type="button" className="btn btn-primary" onClick={onNew}>
          New conversion
        </button>
      </div>
    </section>
  )
}
