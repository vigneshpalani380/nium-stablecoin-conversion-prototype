import { describe, expect, it } from 'vitest'

import { toMinor, validateAmount } from './amount'

describe('toMinor', () => {
  it('converts exactly without floats', () => {
    expect(toMinor('10000.00', 2)).toBe(1000000n)
    expect(toMinor('0.1', 6)).toBe(100000n)
    expect(toMinor('1.500', 2)).toBe(150n) // trailing zeros allowed
    expect(toMinor('1.001', 2)).toBeNull()
  })
})

describe('validateAmount', () => {
  it.each([
    ['', 'Enter an amount.'],
    ['abc', 'Enter a valid amount using digits and an optional decimal point.'],
    ['-5', 'Enter a valid amount using digits and an optional decimal point.'],
    ['1e3', 'Enter a valid amount using digits and an optional decimal point.'],
    ['0', 'Enter an amount greater than zero.'],
    ['0.00', 'Enter an amount greater than zero.'],
    ['1.001', 'This asset supports at most 2 decimal places.'],
    ['25000.01', 'Amount exceeds the available balance.'],
  ])('%s -> %s', (raw, message) => {
    expect(validateAmount(raw, 2, '25000.00')).toBe(message)
  })

  it('accepts a valid amount equal to the available balance', () => {
    expect(validateAmount('25000.00', 2, '25000.00')).toBeNull()
    expect(validateAmount('0.000001', 6, '5000.000000')).toBeNull()
  })
})
