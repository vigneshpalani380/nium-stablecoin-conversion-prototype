import { useEffect, useState } from 'react'

import type { Api } from '../../api/client'
import type { DemoFaults } from '../../api/types'

const COMMIT_SCENARIOS = {
  off: { label: 'Off', faults: { uncertain_commit: 'OFF', recovery_lookup_fails: false } },
  committed: {
    label: 'Settled, ack lost — automated recovery confirms Completed',
    faults: { uncertain_commit: 'COMMITTED', recovery_lookup_fails: false },
  },
  rolled_back: {
    label: 'Rolled back, ack lost — automated recovery releases funds',
    faults: { uncertain_commit: 'ROLLED_BACK', recovery_lookup_fails: false },
  },
  review: {
    label: 'Scenario C — recovery cannot confirm → Under review + ops email',
    faults: { uncertain_commit: 'ROLLED_BACK', recovery_lookup_fails: true },
  },
} as const

function commitScenario(f: DemoFaults): keyof typeof COMMIT_SCENARIOS {
  if (!f.uncertain_commit) return 'off'
  if (f.recovery_lookup_fails) return 'review'
  return f.uncertain_commit === 'COMMITTED' ? 'committed' : 'rolled_back'
}

/** Demo-only fault injection (rendered only when the backend runs in demo mode). */
export function DemoControls({ api }: { api: Api }) {
  const [faults, setFaults] = useState<DemoFaults | null>(null)
  const [message, setMessage] = useState('')

  useEffect(() => {
    api.demo.getFaults().then(setFaults).catch(() => setFaults(null))
  }, [api])

  const update = async (patch: Parameters<Api["demo"]["setFaults"]>[0]) => {
    try {
      setFaults(await api.demo.setFaults(patch))
    } catch {
      setMessage('Could not update demo settings.')
    }
  }

  if (!faults) return null
  return (
    <details className="card demo-panel" style={{ marginTop: 'var(--space-4)' }}>
      <summary>Demo controls (simulated failures)</summary>
      <p className="muted">One-shot faults apply to the next conversion only.</p>
      <label>
        <input
          type="checkbox"
          checked={faults.timeout_after_commit}
          onChange={(e) => update({ timeout_after_commit: e.target.checked })}
        />
        Lose the response after the conversion commits (ambiguous timeout)
      </label>
      <label>
        <input type="checkbox" checked={faults.fail_mid_settle} onChange={(e) => update({ fail_mid_settle: e.target.checked })} />
        Fail during settlement (reservation is released)
      </label>
      <label>
        <input type="checkbox" checked={faults.fail_mid_reserve} onChange={(e) => update({ fail_mid_reserve: e.target.checked })} />
        Fail before the reservation commits (full rollback)
      </label>
      <label>
        <input
          type="checkbox"
          checked={faults.pause_after_reserve_seconds > 0}
          onChange={(e) => update({ pause_after_reserve_seconds: e.target.checked ? 5 : 0 })}
        />
        Pause 5s after reserving (see reserved / pending balances)
      </label>
      <div className="field" style={{ marginTop: 'var(--space-3)' }}>
        <label htmlFor="uncertain-commit">Simulated uncertain database commit (next conversion)</label>
        <select
          id="uncertain-commit"
          value={commitScenario(faults)}
          onChange={(e) => update(COMMIT_SCENARIOS[e.target.value as keyof typeof COMMIT_SCENARIOS].faults)}
        >
          {Object.entries(COMMIT_SCENARIOS).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
        <span className="hint">
          The database connection is lost during the settlement COMMIT. Scenario C: automated recovery cannot confirm the
          outcome, so the conversion goes to internal review and Nium Operations gets a simulated email (internal API only).
        </span>
      </div>
      <div className="actions">
        <button
          type="button"
          className="btn btn-secondary"
          onClick={async () => {
            await api.demo.reset().catch(() => undefined)
            setFaults(await api.demo.getFaults())
            setMessage('Demo data reset. Reload balances to see seed values.')
            window.dispatchEvent(new Event('wallet:refresh'))
          }}
        >
          Reset demo data
        </button>
      </div>
      {message && <p className="muted" role="status">{message}</p>}
    </details>
  )
}
