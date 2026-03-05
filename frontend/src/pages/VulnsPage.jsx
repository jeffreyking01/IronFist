import { useQuery } from '@tanstack/react-query'
import { vulnsApi } from '../api/client'
import { useState } from 'react'

const SEVERITIES = ['', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

export default function VulnsPage() {
  const [severity, setSeverity] = useState('')
  const [kevOnly,  setKevOnly]  = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['vulns', severity, kevOnly],
    queryFn:  () => vulnsApi.list({
      severity:  severity || undefined,
      kev_only:  kevOnly || undefined,
      limit:     200,
    }).then(r => r.data),
  })

  const vulns = data?.items || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold">Vulnerabilities</h1>
          <p className="text-sm text-dim mt-0.5">{data?.total ?? '—'} open findings</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={severity}
            onChange={e => setSeverity(e.target.value)}
            className="bg-surface2 border border-border2 rounded-lg px-3 py-1.5 text-sm text-text outline-none"
          >
            {SEVERITIES.map(s => (
              <option key={s} value={s}>{s || 'All Severities'}</option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm text-mid cursor-pointer">
            <input
              type="checkbox"
              checked={kevOnly}
              onChange={e => setKevOnly(e.target.checked)}
              className="accent-red"
            />
            KEV only
          </label>
        </div>
      </div>

      <div className="card">
        {isLoading && <div className="text-dim text-sm py-8 text-center">Loading...</div>}
        {!isLoading && (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-border">
                {['CVE ID', 'Severity', 'CVSS', 'KEV', 'Status', 'First Detected'].map(h => (
                  <th key={h} className="font-mono text-[10px] text-dim uppercase tracking-wide pb-2 pr-4">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {vulns.map((v) => (
                <tr key={v.id} className="border-b border-border/50 hover:bg-surface2/50">
                  <td className="py-2 pr-4 font-mono text-xs text-text">{v.cve_id}</td>
                  <td className="py-2 pr-4"><SevBadge s={v.severity} /></td>
                  <td className="py-2 pr-4 font-mono text-xs text-mid">{v.cvss_score ?? '—'}</td>
                  <td className="py-2 pr-4">
                    {v.kev_member && <span className="badge badge-kev">KEV</span>}
                  </td>
                  <td className="py-2 pr-4 font-mono text-[10px] text-dim">{v.status}</td>
                  <td className="py-2 font-mono text-[11px] text-dim">
                    {v.first_detected ? new Date(v.first_detected).toLocaleDateString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function SevBadge({ s }) {
  const map = { CRITICAL: 'badge-critical', HIGH: 'badge-high', MEDIUM: 'badge-medium', LOW: 'badge-low' }
  return <span className={`badge ${map[s] || ''}`}>{s}</span>
}
