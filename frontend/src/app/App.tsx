import { useCallback, useEffect, useState } from 'react'

import { api as defaultApi, type Api } from '../api/client'
import type { Account, ConversionConfig } from '../api/types'
import { BalanceCards } from '../components/accounts/BalanceCards'
import { Alert } from '../components/ui/Alert'
import { ActivityList } from '../features/activity/ActivityList'
import { ConvertPage } from '../features/conversion/ConvertPage'

type Tab = 'Balances' | 'Convert' | 'Activity'
const TABS: Tab[] = ['Balances', 'Convert', 'Activity']

export default function App({ api = defaultApi }: { api?: Api }) {
  const [tab, setTab] = useState<Tab>('Balances')
  const [accounts, setAccounts] = useState<Account[] | null>(null)
  const [config, setConfig] = useState<ConversionConfig | null>(null)
  const [loadError, setLoadError] = useState(false)

  const refreshAccounts = useCallback(() => {
    api.getAccounts().then((a) => {
      setAccounts(a)
      setLoadError(false)
    }).catch(() => setLoadError(true))
  }, [api])

  useEffect(() => {
    refreshAccounts()
    api.getConfig().then(setConfig).catch(() => setLoadError(true))
    const onRefresh = () => refreshAccounts()
    window.addEventListener('wallet:refresh', onRefresh)
    return () => window.removeEventListener('wallet:refresh', onRefresh)
  }, [api, refreshAccounts])

  return (
    <div>
      <header className="app-header">
        <span className="wordmark">Nium Wallet Prototype</span>
        <span className="proto-badge">Interview prototype — not production UI · simulated rates</span>
      </header>
      <main className="app-main">
        <h1 className="page-title">Wallet</h1>
        <nav aria-label="Wallet sections" className="tabs">
          {TABS.map((t) => (
            <button key={t} type="button" aria-current={tab === t ? 'page' : undefined} onClick={() => setTab(t)}>
              {t}
            </button>
          ))}
        </nav>

        {loadError && (
          <Alert tone="error" title="Could not reach the wallet service">
            Start the backend (port 8000) and reload.{' '}
            <button type="button" className="btn btn-link" onClick={refreshAccounts}>Retry</button>
          </Alert>
        )}

        {!accounts || !config ? (
          !loadError && <p className="muted">Loading wallet…</p>
        ) : (
          <>
            {tab === 'Balances' && <BalanceCards accounts={accounts} />}
            {tab === 'Convert' && (
              <ConvertPage accounts={accounts} config={config} onBalancesChanged={refreshAccounts} api={api} />
            )}
            {tab === 'Activity' && <ActivityList api={api} />}
          </>
        )}
      </main>
    </div>
  )
}
