const money0 = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
const money2 = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 })
const int = new Intl.NumberFormat('en-US')

export const fmtMoney = (v: number): string => money0.format(v)
export const fmtMoney2 = (v: number): string => money2.format(v)
export const fmtInt = (v: number): string => int.format(Math.round(v))
export const fmtPct = (v: number | null | undefined, digits = 1, sign = true): string => {
  if (v === null || v === undefined || !Number.isFinite(v)) return '—'
  const s = v.toFixed(digits)
  return (sign && v > 0 ? '+' : '') + s + '%'
}
export const fmtRatio = (v: number | null | undefined, digits = 2): string =>
  v === null || v === undefined || !Number.isFinite(v) ? '—' : v.toFixed(digits)
export const fmtSigned = (v: number, digits = 2): string => (v > 0 ? '+' : '') + v.toFixed(digits)
export const shortId = (id: string, head = 8, tail = 4): string =>
  id.length <= head + tail + 1 ? id : `${id.slice(0, head)}…${id.slice(-tail)}`
export const shortUuid = (id: string): string => (id.length > 13 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id)
export const titleCase = (s: string): string =>
  s
    .toLowerCase()
    .replace(/\b([a-z])/g, (m) => m.toUpperCase())
    .replace(/\bInc\b\.?/g, 'Inc.')
    .replace(/\bCorp\b\.?/g, 'Corp.')
    .replace(/\bLlc\b/g, 'LLC')
    .replace(/\bLtd\b/g, 'Ltd')
