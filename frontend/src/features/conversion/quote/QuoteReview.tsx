import type { Quote } from '../../../api/types'
import { formatAmount, formatPercent } from '../../../components/ui/format'

interface Props {
  quote: Quote
  remaining: number
  confirming: boolean
  locked: boolean
  onConfirm: () => void
  onCancel: () => void
  onRequote: () => void
  onDemoExpire?: () => void
}

export function QuoteReview({ quote, remaining, confirming, locked, onConfirm, onCancel, onRequote, onDemoExpire }: Props) {
  const expired = remaining <= 0
  const src = quote.source.asset_code
  const dst = quote.destination.asset_code
  return (
    <section className="card" aria-labelledby="quote-heading">
      <h2 id="quote-heading">Review conversion</h2>
      <p className="muted">
        {quote.source.display_name} → {quote.destination.display_name}
      </p>
      <dl className="summary">
        <dt>You convert (gross)</dt>
        <dd>{formatAmount(quote.gross_source_amount)} {src}</dd>
        <dt>Fee ({formatPercent(quote.fee_rate)})</dt>
        <dd>− {formatAmount(quote.fee_amount)} {quote.fee_currency}</dd>
        <dt>Net amount converted</dt>
        <dd>{formatAmount(quote.net_source_amount)} {src}</dd>
        <dt>
          Rate <span className="sim-label">Simulated demo rate</span>
        </dt>
        <dd>
          1 {src} = {quote.exchange_rate} {dst}
        </dd>
        <div className="total" style={{ display: 'contents' }}>
          <dt>You receive</dt>
          <dd>{formatAmount(quote.destination_amount)} {dst}</dd>
        </div>
      </dl>
      <p className={`expiry num ${expired ? 'expired' : remaining <= 10 ? 'low' : ''}`} aria-live="polite">
        {expired ? 'This quote has expired. Request a new quote.' : `Quote valid for ${remaining}s`}
        <span className="muted"> · Quote {quote.quote_id}</span>
      </p>
      <div className="actions">
        {expired && !locked ? (
          <button type="button" className="btn btn-primary" onClick={onRequote}>
            Get new quote
          </button>
        ) : (
          <button
            type="button"
            className="btn btn-primary"
            onClick={onConfirm}
            disabled={confirming || locked || expired}
            aria-busy={confirming}
          >
            {confirming ? 'Confirming…' : 'Confirm conversion'}
          </button>
        )}
        <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={confirming || locked}>
          Cancel
        </button>
        {onDemoExpire && !expired && !locked && (
          <button type="button" className="btn btn-link" onClick={onDemoExpire} disabled={confirming}>
            Expire this quote (demo)
          </button>
        )}
      </div>
    </section>
  )
}
