import { useQuery } from '@tanstack/react-query'
import { assetsApi } from '../api/client'

export default function AssetsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['assets'],
    queryFn:  () => assetsApi.list({ limit: 100 }).then(r => r.data),
  })

  const assets = data?.items || []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-bold">Assets</h1>
        <p className="text-sm text-dim mt-0.5">
          CMDB — {data?.total ?? '—'} assets tracked
        </p>
      </div>

      <div className="card">
        {isLoading && <div className="text-dim text-sm py-8 text-center">Loading assets...</div>}
        {!isLoading && (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-border">
                {['Hostname', 'IP Address', 'OS', 'Boundary', 'Owner', 'Criticality', 'Last Seen'].map(h => (
                  <th key={h} className="font-mono text-[10px] text-dim uppercase tracking-wide pb-2 pr-4">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {assets.map((a) => (
                <tr key={a.id} className="border-b border-border/50 hover:bg-surface2/50">
                  <td className="py-2 pr-4 font-mono text-xs text-text">{a.hostname || '—'}</td>
                  <td className="py-2 pr-4 font-mono text-xs text-mid">{a.ip_address}</td>
                  <td className="py-2 pr-4 text-mid text-xs">{a.os_name || '—'}</td>
                  <td className="py-2 pr-4">
                    {a.fisma_boundary && (
                      <span className="font-mono text-[10px] bg-blue/10 text-blue border border-blue/20 px-1.5 py-0.5 rounded">
                        {a.fisma_boundary}
                      </span>
                    )}
                  </td>
                  <td className="py-2 pr-4 text-mid text-xs">{a.system_owner || '—'}</td>
                  <td className="py-2 pr-4">
                    <CritBadge c={a.criticality} />
                  </td>
                  <td className="py-2 font-mono text-[11px] text-dim">
                    {a.last_seen ? new Date(a.last_seen).toLocaleDateString() : '—'}
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

function CritBadge({ c }) {
  const map = { HIGH: 'text-red border-red/20 bg-red/5', MEDIUM: 'text-yellow border-yellow/20 bg-yellow/5', LOW: 'text-green border-green/20 bg-green/5' }
  return <span className={`badge ${map[c] || ''}`}>{c}</span>
}
