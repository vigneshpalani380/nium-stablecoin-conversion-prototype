import { useEffect, useState } from 'react'

import { api as defaultApi, ApiError, type Api } from '../../api/client'
import type { Account, ConversionConfig, Quote, Transaction } from '../../api/types'
import { Alert } from '../../components/ui/Alert'
import { DemoControls } from './DemoControls'
import { ConversionForm, type FormValues } from './form/ConversionForm'
import { QuoteReview } from './quote/QuoteReview'
import { useCountdown } from './quote/useCountdown'
import { BalanceChange, ConversionResult } from './result/ConversionResult'
import { UnderReview } from './result/UnderReview'
import { useConfirmConversion, type ConfirmOptions } from './useConfirmConversion'

interface Props {
  accounts: Account[]
  config: ConversionConfig
  onBalancesChanged: () => void
  api?: Api
  confirmOptions?: ConfirmOptions
}

const EMPTY: FormValues = { sourceId: '', destinationId: '', amount: '' }

export function ConvertPage({ accounts, config, onBalancesChanged, api = defaultApi, confirmOptions }: Props) {
  const [values, setValues] = useState<FormValues>(EMPTY)
  const [quote, setQuote] = useState<Quote | null>(null)
  const [quoteError, setQuoteError] = useState<ApiError | null>(null)
  const [quoting, setQuoting] = useState(false)
  const [reviewTxn, setReviewTxn] = useState<Transaction | null>(null)
  const remaining = useCountdown(quote)
  const { state, confirm, checkAgain, idempotencyKey } = useConfirmConversion(quote?.quote_id ?? null, {
    api,
    ...confirmOptions,
  })

  const inFlight = state.kind === 'submitting' || state.kind === 'checking'
  // Once a confirm has been attempted, the quote is locked to its idempotency key.
  const locked = state.kind !== 'idle' && state.kind !== 'rejected'

  // Refresh balances while a conversion is in flight (shows reserved/pending) and when it ends.
  useEffect(() => {
    if (!inFlight) return
    const id = setInterval(onBalancesChanged, 1000)
    return () => clearInterval(id)
  }, [inFlight, onBalancesChanged])
  useEffect(() => {
    if (state.kind !== 'idle' && !inFlight) onBalancesChanged()
  }, [state.kind, inFlight, onBalancesChanged])

  // Keep the Under review view on screen while the customer refreshes its status.
  useEffect(() => {
    if (state.kind === 'under_review') setReviewTxn(state.transaction)
    else if (state.kind === 'completed' || state.kind === 'failed' || state.kind === 'idle') setReviewTxn(null)
  }, [state])

  const changeInputs = (next: FormValues) => {
    setValues(next)
    if (quote) {
      // Inputs changed: the old quote no longer matches. Discard it.
      api.cancelQuote(quote.quote_id).catch(() => undefined)
      setQuote(null)
    }
    setQuoteError(null)
  }

  const requestQuote = async () => {
    setQuoting(true)
    setQuoteError(null)
    try {
      setQuote(await api.createQuote(values.sourceId, values.destinationId, values.amount.trim()))
    } catch (err) {
      setQuote(null)
      setQuoteError(err instanceof ApiError ? err : new ApiError(0, 'NETWORK', 'Could not reach the server. Try again.'))
    } finally {
      setQuoting(false)
    }
  }

  const cancel = () => {
    if (quote) api.cancelQuote(quote.quote_id).catch(() => undefined)
    setQuote(null)
  }

  const startOver = () => {
    setReviewTxn(null)
    setQuote(null)
    setValues(EMPTY)
    setQuoteError(null)
  }

  const demoExpire = config.demo_mode && quote
    ? async () => {
        await api.demo.expireQuote(quote.quote_id).catch(() => undefined)
        // Keep the countdown honest: the server now considers the quote expired.
        setQuote({ ...quote, seconds_remaining: 0 })
      }
    : undefined

  if (reviewTxn && (state.kind === 'under_review' || state.kind === 'checking' || state.kind === 'unresolved')) {
    return (
      <>
        <UnderReview
          transaction={state.kind === 'under_review' ? state.transaction : reviewTxn}
          accounts={accounts}
          checking={state.kind === 'checking'}
          onRefresh={checkAgain}
        />
        {config.demo_mode && <DemoControls api={api} />}
      </>
    )
  }

  if (state.kind === 'completed') {
    return (
      <>
        <ConversionResult transaction={state.transaction} recovered={state.recovered} onNew={startOver} />
        {config.demo_mode && <DemoControls api={api} />}
      </>
    )
  }

  return (
    <>
      <ConversionForm
        accounts={accounts}
        config={config}
        values={values}
        onChange={changeInputs}
        onSubmit={requestQuote}
        busy={quoting}
        disabled={locked}
      />
      {quoteError && <QuoteErrorAlert error={quoteError} />}

      {quote && (
        <QuoteReview
          quote={quote}
          remaining={remaining}
          confirming={inFlight}
          locked={locked}
          onConfirm={confirm}
          onCancel={cancel}
          onRequote={requestQuote}
          onDemoExpire={demoExpire}
        />
      )}

      <ConfirmStatus
        state={state}
        reference={idempotencyKey}
        onCheckAgain={checkAgain}
        onRetrySameKey={confirm}
        onRequote={requestQuote}
        onStartOver={startOver}
      />

      {config.demo_mode && <DemoControls api={api} />}
    </>
  )
}

function QuoteErrorAlert({ error }: { error: ApiError }) {
  const titles: Record<string, string> = {
    UNSUPPORTED_PAIR: 'Conversion pair not available',
    INSUFFICIENT_BALANCE: 'Insufficient balance',
    PRECISION_EXCEEDED: 'Too many decimal places',
    INVALID_AMOUNT: 'Invalid amount',
    SAME_ACCOUNT: 'Same account selected',
  }
  return (
    <Alert tone="error" title={titles[error.code] ?? 'Could not get a quote'}>
      {error.message}
    </Alert>
  )
}

function ConfirmStatus({
  state,
  reference,
  onCheckAgain,
  onRetrySameKey,
  onRequote,
  onStartOver,
}: {
  state: ReturnType<typeof useConfirmConversion>['state']
  reference: string
  onCheckAgain: () => void
  onRetrySameKey: () => void
  onRequote: () => void
  onStartOver: () => void
}) {
  switch (state.kind) {
    case 'checking':
      return (
        <Alert tone="info" title="Checking conversion status…">
          We did not get a clear response, so we are checking the original request (attempt {state.attempt}). Please
          do not resubmit. Reference: <span className="mono">{reference}</span>
        </Alert>
      )
    case 'rejected': {
      const e = state.error
      if (e.code === 'QUOTE_EXPIRED' || e.code === 'QUOTE_CANCELLED') {
        return (
          <Alert tone="warning" title="Quote expired">
            {e.message} No funds were moved.{' '}
            <button type="button" className="btn-link btn" onClick={onRequote}>Get new quote</button>
          </Alert>
        )
      }
      if (e.code === 'INSUFFICIENT_BALANCE') {
        return <Alert tone="error" title="Insufficient balance">{e.message} No funds were moved.</Alert>
      }
      if (e.code === 'IDEMPOTENCY_CONFLICT') {
        return <Alert tone="error" title="Reference already used">{e.message} Start a new conversion.</Alert>
      }
      if (e.code === 'QUOTE_ALREADY_USED') {
        return <Alert tone="warning" title="Quote already used">{e.message}</Alert>
      }
      return <Alert tone="error" title="Conversion not submitted">{e.message}</Alert>
    }
    case 'failed':
      return (
        <Alert tone="error" title="Conversion failed — funds released">
          {state.error.message} No balance was debited.
          {state.transaction && (
            <div className="snapshot-grid">
              <BalanceChange label={state.transaction.source.display_name} asset={state.transaction.source.asset_code} {...state.transaction.balances.source} />
            </div>
          )}
          <div className="actions">
            <button type="button" className="btn btn-secondary" onClick={onStartOver}>Start a new conversion</button>
          </div>
        </Alert>
      )
    case 'not_received':
      return (
        <Alert tone="warning" title="Conversion not received">
          The server has no record of this request, so no funds moved. You can safely retry: the retry reuses the same
          reference, so it can never create a duplicate. Reference: <span className="mono">{reference}</span>
          <div className="actions">
            <button type="button" className="btn btn-primary" onClick={onRetrySameKey}>Retry with same reference</button>
          </div>
        </Alert>
      )
    case 'unresolved':
      return (
        <Alert tone="warning" title="Status not yet confirmed">
          We could not confirm the outcome yet. The conversion may still complete. Do not submit a new conversion; check
          again in a moment or check Activity. Reference: <span className="mono">{reference}</span>
          {state.transactionId && <> · Transaction <span className="mono">{state.transactionId}</span></>}
          <div className="actions">
            <button type="button" className="btn btn-secondary" onClick={onCheckAgain}>Check status again</button>
          </div>
        </Alert>
      )
    default:
      return null
  }
}
