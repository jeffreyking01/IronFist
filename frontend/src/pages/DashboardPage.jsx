import { useQuery } from '@tanstack/react-query'
import { dashboardApi, vulnsApi } from '../api/client'
import { AlertTriangle, Server, Plug, ShieldAlert } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

export default function DashboardPage() {
  const { data: summary, isLoading } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn:  () => dashboardApi.summary().then(r => r.data),
    refetchInterval: 60_000,
  })

  const { data: kevData } = useQuery({
    queryKey: ['kev-watch'],
    queryFn:  () => vulnsApi.kev().then(r => r.data),
  })

  if (isLoading) return <LoadingState />

  const sevData = [
    { name: 'Critical', value: summary?.vulnerabilities?.critical || 0, color: '#ff4d4d' },
    { name: 'High',     value: summary?.vulnerabilities?.high     || 0, color: '#ff7b2e' },
    { name: 'Medium',   value: summary?.vulnerabilities?.medium   || 0, color: '#ffc53d' },
    { name: 'Low',      value: summary?.vulnerabilities?.low      || 0, color: '#00d68f' },
  ]

  const totalVulns = sevData.reduce((sum, s) => sum + s.value, 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-bold">Dashboard</h1>
        <p className="text-sm text-dim mt-0.5">Vulnerability posture overview</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4">
        <KPICard
          label="Critical Findings"
          value={summary?.vulnerabilities?.critical ?? '—'}
          color="text-red"
          bg="bg-red/5 border-red/20"
          icon={<ShieldAlert size={18} className="text-red" />}
        />
        <KPICard
          label="KEV Findings"
          value={summary?.kev?.total ?? '—'}
          sub={summary?.kev?.overdue ? `${summary.kev.overdue} overdue` : null}
          subColor="text-red"
          color="text-orange"
          bg="bg-orange/5 border-orange/20"
          icon={<AlertTriangle size={18} className="text-orange" />}
        />
        <KPICard
          label="Total Assets"
          value={summary?.assets?.total ?? '—'}
          sub={summary?.assets?.stale ? `${summary.assets.stale} stale` : 'All current'}
          color="text-blue"
          bg="bg-blue/5 border-blue/20"
          icon={<Server size={18} className="text-blue" />}
        />
        <KPICard
          label="Active Connectors"
          value={summary?.connectors?.active ?? '—'}
          color="text-green"
          bg="bg-green/5 border-green/20"
          icon={<Plug size={18} className="text-green" />}
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-2 gap-4">
        {/* Severity breakdown */}
        <div className="card">
          <h2 className="font-semibold text-sm mb-4">Open Vulnerabilities by Severity</h2>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={sevData} barSize={32}>
              <XAxis dataKey="name" tick={{ fill: '#7a9ab8', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#7a9ab8', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: '#0d1420', border: '1px solid #243550', borderRadius: 8, fontSize: 12 }}
                cursor={{ fill: 'rgba(255,255,255,0.03)' }}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {sevData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-2 text-right font-mono text-xs text-dim">
            {totalVulns} total open findings
          </div>
        </div>

        {/* KEV watch summary */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-sm">KEV Watch — Due Soonest</h2>
            <a href="/kev" className="font-mono text-[10px] text-blue hover:underline">
              View all →
            </a>
          </div>
          {kevData?.length === 0 && (
            <div className="text-sm text-dim text-center py-8">No open KEV findings</div>
          )}
          <div className="space-y-2">
            {(kevData || []).slice(0, 5).map((v) => (
              <div key={v.id} className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
                <div className="flex items-center gap-2">
                  <span className="badge badge-kev">KEV</span>
                  <span className="font-mono text-xs text-text">{v.cve_id}</span>
                </div>
                <div className="flex items-center gap-3 text-[11px]">
                  <span className="text-mid">{v.asset_hostname || v.asset_id?.slice(0,8)}</span>
                  {v.kev_due_date && (
                    <span className={isDue(v.kev_due_date) ? 'text-red font-mono' : 'text-dim font-mono'}>
                      {formatDate(v.kev_due_date)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function KPICard({ label, value, sub, subColor, color, bg, icon }) {
  return (
    <div className={`card border ${bg} flex items-start justify-between`}>
      <div>
        <div className="text-xs text-dim mb-1">{label}</div>
        <div className={`text-3xl font-bold ${color}`}>{value}</div>
        {sub && <div className={`text-[11px] mt-1 ${subColor || 'text-dim'}`}>{sub}</div>}
      </div>
      <div className="mt-1">{icon}</div>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="space-y-6">
      <div className="h-6 w-32 bg-surface2 rounded animate-pulse" />
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="card h-24 animate-pulse bg-surface2" />
        ))}
      </div>
    </div>
  )
}

function isDue(dateStr) {
  return new Date(dateStr) < new Date()
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
