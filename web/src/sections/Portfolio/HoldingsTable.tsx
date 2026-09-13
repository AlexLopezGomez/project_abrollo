import { useMemo, useState } from 'react'
import styles from './Portfolio.module.css'
import type { TickerRow } from '../../data/schema'
import { fmtMoney, fmtMoney2, fmtPct, titleCase } from '../../lib/format'

type Key = 'ticker' | 'name' | 'amount' | 'weightPct' | 'purchasePrice' | 'evalPrice' | 'value' | 'returnPct'

const COLS: { key: Key; label: string }[] = [
  { key: 'ticker', label: 'Ticker' },
  { key: 'name', label: 'Entity' },
  { key: 'amount', label: 'Invested' },
  { key: 'weightPct', label: 'Weight' },
  { key: 'purchasePrice', label: 'Apr-15-25' },
  { key: 'evalPrice', label: 'Apr-15-26' },
  { key: 'value', label: 'Value' },
  { key: 'returnPct', label: 'Return' },
]

export function HoldingsTable({ rows }: { rows: TickerRow[] }) {
  const [sort, setSort] = useState<{ key: Key; dir: 1 | -1 }>({ key: 'returnPct', dir: -1 })
  const sorted = useMemo(() => {
    const out = [...rows]
    out.sort((a, b) => {
      const va = a[sort.key]
      const vb = b[sort.key]
      if (typeof va === 'string' && typeof vb === 'string') return va.localeCompare(vb) * sort.dir
      return ((va as number | null) ?? -Infinity) > ((vb as number | null) ?? -Infinity) ? sort.dir : -sort.dir
    })
    return out
  }, [rows, sort])

  const toggle = (key: Key) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === 1 ? -1 : 1 } : { key, dir: key === 'ticker' || key === 'name' ? 1 : -1 }))

  return (
    <div className={`card ${styles.tableWrap}`} data-table>
      <table className={styles.table}>
        <thead>
          <tr>
            {COLS.map((c) => (
              <th key={c.key} className={sort.key === c.key ? styles.sorted : ''} onClick={() => toggle(c.key)}>
                {c.label}
                {sort.key === c.key ? (sort.dir === 1 ? ' ↑' : ' ↓') : ''}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={r.ticker}>
              <td>{r.ticker}</td>
              <td className={styles.name} title={r.name}>
                {titleCase(r.name)}
              </td>
              <td>{fmtMoney(r.amount)}</td>
              <td>{r.weightPct.toFixed(2)}%</td>
              <td>{r.purchasePrice === null ? '—' : fmtMoney2(r.purchasePrice)}</td>
              <td>{r.evalPrice === null ? '—' : fmtMoney2(r.evalPrice)}</td>
              <td>{r.value === null ? '—' : fmtMoney(r.value)}</td>
              <td className={(r.returnPct ?? 0) >= 0 ? 'up' : 'down'}>{fmtPct(r.returnPct)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
