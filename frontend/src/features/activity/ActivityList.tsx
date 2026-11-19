import { useEffect, useState } from 'react'

import { api as defaultApi, type Api } from '../../api/client'
import type { Transaction } from '../../api/types'
import { Alert } from '../../components/ui/Alert'
import { formatAmount, formatDateTime } from '../../components/ui/format'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { BalanceChange } from '../conversion/result/ConversionResult'

export function ActivityList({ api = defaultApi }: { api?: Api }) {
  const [items, setItems] = useState<Transaction[] | null>(null)
  const [error, setError] = useState(false)
  const [selected, setSelected] = useState<Transaction | null>(null)

  const load = () => {
    setError(false)
    api.listTransactions().then(setItems).catch(() => setError(true))
  }
  useEffect(load, [api])

  if (error) return <Alert tone="error" title="Could not load activity">Check that the backend is running and try again.</Alert>
  if (!items) return <p className="muted">Loading activity…</p>
  if (items.length === 0) return <div className="card"><p className="muted">No conversions yet.</p></div>

  return (
    <>
      <section className="card" aria-labelledby="activity-heading">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
          <h2 id="activity-heading" style={{ margin: 0 }}>Recent conversions</h2>
          <button type="button" className="btn btn-secondary" onClick={load}>Refresh</button>
        </div>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th scope="col">Date / time</th>
                <th scope="col" className="num">From</th>
                <th scope="col" className="num">To</th>
                <th scope="col" className="num">Fee</th>
                <th scope="col">Status</th>
                <th scope="col">Transaction</th>
              </tr>
            </thead>
            <tbody>
              {items.map((t) => (
                <tr
                  key={t.transaction_id}
                  tabIndex={0}
                  aria-selected={selected?.transaction_id === t.transaction_id}
                  onClick={() => setSelected(t)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      setSelected(t)
                    }
                  }}
                >
                  <td>{formatDateTime(t.created_at)}</td>
                  <td className="num">{formatAmount(t.gross_source_amount)} {t.source.display_name}</td>
                  <td className="num">{formatAmount(t.destination_amount)} {t.destination.display_name}</td>
                  <td className="num">{formatAmount(t.fee_amount)} {t.fee_currency}</td>
                  <td><StatusBadge status={t.status} /></td>
                  <td className="mono">{t.transaction_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {selected && <TransactionDetail t={selected} onClose={() => setSelected(null)} />}
    </>
  )
}

export function TransactionDetail({ t, onClose }: { t: Transaction; onClose: () => void }) {
  return (
    <section className="card" aria-labelledby="detail-heading">
      <h2 id="detail-heading">
        Transaction detail <StatusBadge status={t.status} />
      </h2>
      <dl className="summary">
        <dt>Transaction</dt><dd className="mono">{t.transaction_id}</dd>
        <dt>Quote</dt><dd className="mono">{t.quote_id}</dd>
        <dt>Reference (idempotency key)</dt><dd className="mono">{t.idempotency_key}</dd>
        <dt>Gross / fee / net</dt>
        <dd>{formatAmount(t.gross_source_amount)} / {formatAmount(t.fee_amount)} / {formatAmount(t.net_source_amount)} {t.source.asset_code}</dd>
        <dt>Rate ({t.rate_source.toLowerCase()})</dt>
        <dd>1 {t.source.asset_code} = {t.exchange_rate} {t.destination.asset_code}</dd>
        <dt>{t.status === 'REVIEW_REQUIRED' ? 'Expected to receive' : 'Received'}</dt>
        <dd>
          {formatAmount(t.destination_amount)} {t.destination.display_name}
          {t.status === 'REVIEW_REQUIRED' && <strong> — not yet confirmed</strong>}
        </dd>
        <dt>Reserved at</dt><dd>{formatDateTime(t.reserved_at)}</dd>
        {t.status !== 'REVIEW_REQUIRED' && (
          <>
            <dt>{t.status === 'FAILED' ? 'Released at' : 'Settled at'}</dt>
            <dd>{formatDateTime(t.status === 'FAILED' ? t.released_at : t.settled_at)}</dd>
          </>
        )}
        <dt>Last updated</dt><dd>{formatDateTime(t.last_updated_at)}</dd>
        {t.failure_code && (<><dt>Failure</dt><dd>{t.failure_code}: {t.failure_message}</dd></>)}
      </dl>
      <div className="snapshot-grid">
        <BalanceChange label={t.source.display_name} asset={t.source.asset_code} {...t.balances.source} />
        <BalanceChange label={t.destination.display_name} asset={t.destination.asset_code} {...t.balances.destination} />
      </div>
      <div className="actions">
        <button type="button" className="btn btn-secondary" onClick={onClose}>Close</button>
      </div>
    </section>
  )
}
