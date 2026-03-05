import { useQuery } from '@tanstack/react-query'
import { vulnsApi } from '../api/client'
import { AlertTriangle } from 'lucide-react'

export default function KEVPage() {
  const { data: kevItems = [], isLoading } = useQuery({
    queryKey: ['kev-watch'],
    queryFn:  () => vulnsApi.kev().then(r => r.data),
    refetchInterval: 60_000,
  })

  const overdue  = kevItems.filter(v => v.kev_due_date && new Date(v.kev_due_date) < new Date())
  const upcoming = kevItems.filter(v => !v.kev_due_date || new Date(v.kev_due_date) >= new Date())

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold flex items-center gap-2">
            <AlertTriangle size={18} className="text-orange" />
            KEV Watch
          </h1>
          <p className="text-sm text-dim mt-0.5">
            CISA Known Exploited Vulnerabilities — BOD 22-01 tracking
          </p>
        </div>
        <div className="flex gap-3">
          <Stat label="Total KEV"  value={kevItems.length}  color="text-text" />
          <Stat label="Overdue"    value={overdue.length}   color="text-red"  />
          <Stat label="Upcoming"   value={upcoming.length}  color="text-yellow" />
        </div>
      </div>

      {isLoading && <div className="text-dim text-sm">Loading KEV data...</div>}

      {overdue.length > 0 && (
        <Section title="Overdue" titleColor="text-red" items={overdue} />
      )}
      {upcoming.length > 0 && (
        <Section title="Upcoming / No Due Date" titleColor="text-yellow" items={upcoming} />
      )}
      {!isLoading && kevItems.length === 0 && (
        <div className="card text-center py-12 text-dim">
          No open KEV findings. Run a sync to populate data.
        </div>
      )}
    </div>
  )
}

function Section({ title, titleColor, items }) {
  return (
    <div className="card">
      <h2 className={`font-semibold text-sm mb-3 ${titleColor}`}>{title} — {items.length}</h2>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b border-border">
            <th className="font-mono text-[10px] text-dim uppercase tracking-wide pb-2 pr-4">CVE ID</th>
            <th className="font-mono text-[10px] text-dim uppercase tracking-wide pb-2 pr-4">Asset</th>
            <th className="font-mono text-[10px] text-dim uppercase tracking-wide pb-2 pr-4">Boundary</th>
            <th className="font-mono text-[10px] text-dim uppercase tracking-wide pb-2 pr-4">Severity</th>
            <th className="font-mono text-[10px] text-dim uppercase tracking-wide pb-2">Due Date</th>
          </tr>
        </thead>
        <tbody>
          {items.map((v) => (
            <tr key={v.id} className="border-b border-border/50 hover:bg-surface2/50">
              <td className="py-2 pr-4 font-mono text-xs text-text">{v.cve_id}</td>
              <td className="py-2 pr-4 text-mid">{v.asset_hostname || '—'}</td>
              <td className="py-2 pr-4">
                <span className="font-mono text-[10px] bg-blue/10 text-blue border border-blue/20 px-1.5 py-0.5 rounded">
                  {v.asset_boundary || '—'}
                </span>
              </td>
              <td className="py-2 pr-4">
                <SeverityBadge severity={v.severity} />
              </td>
              <td className="py-2 font-mono text-xs">
                {v.kev_due_date
                  ? <span className={new Date(v.kev_due_date) < new Date() ? 'text-red' : 'text-yellow'}>
                      {formatDate(v.kev_due_date)}
                    </span>
                  : <span className="text-dim">—</span>
                }
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Stat({ label, value, color }) {
  return (
    <div className="card text-center px-5 py-2">
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-[10px] text-dim mt-0.5">{label}</div>
    </div>
  )
}

function SeverityBadge({ severity }) {
  const map = {
    CRITICAL: 'badge-critical',
    HIGH:     'badge-high',
    MEDIUM:   'badge-medium',
    LOW:      'badge-low',
  }
  return <span className={`badge ${map[severity] || ''}`}>{severity}</span>
}

function formatDate(d) {
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
