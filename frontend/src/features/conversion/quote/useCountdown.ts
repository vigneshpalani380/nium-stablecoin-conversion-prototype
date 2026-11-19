import { useEffect, useState } from 'react'

import type { Quote } from '../../../api/types'

/** Countdown based on the server's seconds_remaining, so client clock skew does not matter. */
export function useCountdown(quote: Quote | null): number {
  const [remaining, setRemaining] = useState(quote?.seconds_remaining ?? 0)
  useEffect(() => {
    if (!quote) return
    const receivedAt = Date.now()
    const tick = () => setRemaining(Math.max(0, quote.seconds_remaining - Math.floor((Date.now() - receivedAt) / 1000)))
    tick()
    const id = setInterval(tick, 250)
    return () => clearInterval(id)
  }, [quote])
  return remaining
}
