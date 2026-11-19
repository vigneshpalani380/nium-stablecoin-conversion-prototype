import type { Account } from '../../api/types'
import { formatAmount, isZero } from '../ui/format'

function networkLabel(a: Account): string {
  return a.network ? `${a.network.charAt(0)}${a.network.slice(1).toLowerCase()}` : 'Fiat'
}

export function BalanceCards({ accounts }: { accounts: Account[] }) {
  return (
    <div className="balance-grid">
      {accounts.map((a) => (
        <article key={a.id} className="card balance-card" aria-label={`${a.display_name} balance`}>
          <div className="asset-row">
            <span className="asset">{a.asset_code}</span>
            <span className="network">{networkLabel(a)}</span>
          </div>
          <p className="amount">
            {formatAmount(a.available_balance)} <span className="label">{a.asset_code}</span>
          </p>
          <div className="label">Available</div>
          {(!isZero(a.reserved_balance) || !isZero(a.pending_balance)) && (
            <div className="holds num">
              {!isZero(a.reserved_balance) && (
                <span className="reserved">Reserved: {formatAmount(a.reserved_balance)} (outgoing, in progress)</span>
              )}
              {!isZero(a.pending_balance) && (
                <span className="pending">Pending: {formatAmount(a.pending_balance)} (incoming, not yet available)</span>
              )}
            </div>
          )}
        </article>
      ))}
    </div>
  )
}
