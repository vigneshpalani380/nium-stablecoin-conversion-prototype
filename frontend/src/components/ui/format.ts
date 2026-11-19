// Display-only formatting of decimal strings. Pure string manipulation, never floats.

/** "14950.000000" -> "14,950.00"; "0.000123" -> "0.000123". Keeps at least 2 decimals, trims extra zeros. */
export function formatAmount(value: string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  const negative = value.startsWith('-')
  const raw = negative ? value.slice(1) : value
  const [intPart, frac = ''] = raw.split('.')
  let decimals = frac.replace(/0+$/, '')
  if (decimals.length < 2) decimals = (decimals + '00').slice(0, Math.max(2, decimals.length))
  const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return `${negative ? '-' : ''}${grouped}.${decimals}`
}

export function isZero(value: string | null | undefined): boolean {
  return !value || /^-?0*(\.0*)?$/.test(value)
}

/** "0.005" -> "0.5%" without float arithmetic (shift decimal point two places). */
export function formatPercent(rate: string): string {
  const [i, f = ''] = rate.split('.')
  const padded = (f + '00')
  const whole = String(Number(i) * 100 + Number(padded.slice(0, 2)))
  const rest = padded.slice(2).replace(/0+$/, '')
  return `${whole}${rest ? '.' + rest : ''}%`
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'medium' })
}
