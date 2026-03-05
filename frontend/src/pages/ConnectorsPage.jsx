import { useQuery } from '@tanstack/react-query'
import { connectorsApi, syncApi } from '../api/client'
import { useState } from 'react'
import { RefreshCw, CheckCircle, XCircle, AlertCircle } from 'lucide-react'

export default function ConnectorsPage() {
  const { data: connectors = [], isLoading, refetch } = useQuery({
    queryKey: ['connectors'],
    queryFn:  () => connectorsApi.list().then(r => r.data),
    refetchInterval: 15_000,
  })

  const [syncing, setSyncing] = useState(null)

  const handleSync = async (type) => {
    setSyncing(type)
    try {
      if (type === 'kev')     await syncApi.kev()
      if (type === 'tenable') await syncApi.tenable()
      if (type === 'all')     await syncApi.all()
      setTimeout(() => { refetch(); setSyncing(null) }, 2000)
    } catch { setSyncing(null) }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold">Connectors</h1>
          <p className="text-sm text-dim mt-0.5">Data source integrations</p>
        </div>
        <button
          onClick={() => handleSync('all')}
          disabled={!!syncing}
          className="btn-ghost flex items-center gap-2 text-sm"
        >
          <RefreshCw size={14} className={syncing === 'all' ? 'animate-spin' : ''} />
          Sync All
        </button>
      </div>

      {isLoading && <div className="text-dim text-sm">Loading connectors...</div>}

      <div className="grid gap-4">
        {connectors.map((c) => (
          <div key={c.id} className="card flex items-center justify-between">
            <div className="flex items-center gap-4">
              <StatusIcon status={c.status} />
              <div>
                <div className="font-semibold text-sm">{c.name}</div>
                <div className="font-mono text-[10px] text-dim uppercase mt-0.5">
                  {c.type} · Every {c.schedule_hours}h
                  {c.tls_verified && ' · TLS verified'}
                </div>
                {c.last_error && (
                  <div className="text-[11px] text-red mt-1">{c.last_error}</div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-6">
              <div className="text-right">
                <div className="font-mono text-xs text-mid">
                  {c.last_sync_count ?? '—'} records
                </div>
                <div className="font-mono text-[10px] text-dim">
                  {c.last_sync_at
                    ? new Date(c.last_sync_at).toLocaleString()
                    : 'Never synced'}
                </div>
              </div>
              <button
                onClick={() => handleSync(c.name.includes('kev') ? 'kev' : 'tenable')}
                disabled={!!syncing}
                className="btn-ghost text-xs flex items-center gap-1.5 py-1.5"
              >
                <RefreshCw size={12} className={syncing ? 'animate-spin' : ''} />
                Sync
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function StatusIcon({ status }) {
  if (status === 'ACTIVE')   return <CheckCircle size={18} className="text-green flex-shrink-0" />
  if (status === 'ERROR')    return <XCircle     size={18} className="text-red flex-shrink-0" />
  return                            <AlertCircle  size={18} className="text-yellow flex-shrink-0" />
}
