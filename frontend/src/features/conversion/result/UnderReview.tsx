import type { Account, Transaction } from '../../../api/types'
import { formatAmount, formatDateTime } from '../../../components/ui/format'
import { StatusBadge } from '../../../components/ui/StatusBadge'

export const UNDER_REVIEW_MESSAGE =
  "We couldn't confirm the final settlement status of your conversion. Your funds remain reserved while our " +
  "operations team investigates. You do not need to submit the conversion again. We'll notify you when the " +
  'status is resolved.'

/** Customer view of an unresolved conversion. Shows no internal review, notification or log details. */
export function UnderReview({
  transaction: t,
  accounts,
  checking,
  onRefresh,
}: {
  transaction: Transaction
  accounts: Account[]
  checking: boolean
  onRefresh: () => void
}) {
  const src = accounts.find((a) => a.id === t.source.account_id)
  const dst = accounts.find((a) => a.id === t.destination.account_id)
  return (
    <section className="card" aria-labelledby="review-heading">
      <h2 id="review-heading">
        Conversion under review <StatusBadge status="REVIEW_REQUIRED" />
      </h2>
      <div className="alert alert-warning" role="status" style={{ marginTop: 0 }}>
        <strong>Status: Under review</strong>
        {UNDER_REVIEW_MESSAGE}
      </div>
      <dl className="summary" style={{ marginTop: 'var(--space-3)' }}>
        <dt>Conversion ID</dt>
        <dd className="mono">{t.transaction_id}</dd>
        <dt>From</dt>
        <dd>{formatAmount(t.gross_source_amount)} {t.source.display_name}</dd>
        <dt>To</dt>
        <dd>{formatAmount(t.destination_amount)} {t.destination.display_name}</dd>
        <dt>Current status</dt>
        <dd>Under review</dd>
        <dt>Source reserved</dt>
        <dd>
          {formatAmount(t.gross_source_amount)} {t.source.asset_code}
          {src && <span className="muted"> (account reserved total {formatAmount(src.reserved_balance)})</span>}
        </dd>
        <dt>Destination credit</dt>
        <dd>
          {formatAmount(t.destination_amount)} {t.destination.asset_code} — <strong>not yet confirmed</strong>
          {dst && <span className="muted"> (pending {formatAmount(dst.pending_balance)})</span>}
        </dd>
        <dt>Last updated</dt>
        <dd>{formatDateTime(t.last_updated_at)}</dd>
      </dl>
      <div className="actions">
        <button type="button" className="btn btn-secondary" onClick={onRefresh} disabled={checking}>
          {checking ? 'Checking…' : 'Refresh status'}
        </button>
      </div>
    </section>
  )
}
