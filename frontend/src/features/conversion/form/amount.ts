// Client-side amount validation for fast feedback. The backend re-validates everything.
// Uses BigInt minor units: no floating-point arithmetic on money.

const AMOUNT_RE = /^\d{1,12}(\.\d+)?$/

/** Convert a validated decimal string to integer minor units. Returns null if it has excess precision. */
export function toMinor(value: string, precision: number): bigint | null {
  if (!AMOUNT_RE.test(value)) return null
  const [intPart, frac = ''] = value.split('.')
  const trimmed = frac.replace(/0+$/, '')
  if (trimmed.length > precision) return null
  return BigInt(intPart + frac.padEnd(precision, '0').slice(0, precision))
}

export function validateAmount(raw: string, precision: number, available: string | undefined): string | null {
  const value = raw.trim()
  if (value === '') return 'Enter an amount.'
  if (!AMOUNT_RE.test(value)) return 'Enter a valid amount using digits and an optional decimal point.'
  const minor = toMinor(value, precision)
  if (minor === null) return `This asset supports at most ${precision} decimal places.`
  if (minor === 0n) return 'Enter an amount greater than zero.'
  if (available !== undefined) {
    const availMinor = toMinor(available, precision)
    if (availMinor !== null && minor > availMinor) return 'Amount exceeds the available balance.'
  }
  return null
}
