import { describe, expect, it } from 'vitest'

import { formatAmount, formatPercent, isZero } from './format'

describe('formatAmount', () => {
  it.each([
    ['14950.000000', '14,950.00'],
    ['25000.00', '25,000.00'],
    ['0.000123', '0.000123'],
    ['1195.194995', '1,195.194995'],
    ['2000000.5', '2,000,000.50'],
    ['7', '7.00'],
  ])('%s -> %s', (input, output) => expect(formatAmount(input)).toBe(output))
})

it('formatPercent shifts the decimal without floats', () => {
  expect(formatPercent('0.005')).toBe('0.5%')
  expect(formatPercent('0.0125')).toBe('1.25%')
})

it('isZero', () => {
  expect(isZero('0.000000')).toBe(true)
  expect(isZero('0.000001')).toBe(false)
})
