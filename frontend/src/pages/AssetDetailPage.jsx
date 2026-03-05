import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, useNavigate } from 'react-router-dom'
import { assetsApi } from '../api/client'
import { useState } from 'react'
import {
  ArrowLeft, Server, Cpu, Network, Package,
  ShieldAlert, Edit2, Check, X, AlertTriangle, ChevronDown
} from 'lucide-react'

export default function AssetDetailPage() {
  const { id }       = useParams()
  const navigate     = useNavigate()
  const queryClient  = useQueryClient()

  const { data: asset, isLoading } = useQuery({
    queryKey: ['asset', id],
    queryFn:  () => assetsApi.get(id).then(r => r.data),
  })

  const mutation = useMutation({
    mutationFn: (data) => assetsApi.patch(id, data),
    onSuccess:  () => queryClient.invalidateQueries(['asset', id]),
  })

  if (isLoading) return <div className="text-dim text-sm p-4">Loading asset...</div>
  if (!asset)    return <div className="text-red text-sm p-4">Asset not found.</div>

  return (
    <div className="space-y-5 max-w-5xl">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate('/assets')}
          className="flex items-center gap-1.5 text-dim hover:text-text text-sm mb-3 transition-colors"
        >
          <ArrowLeft size={14} /> Back to Assets
        </button>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue/10 border border-blue/20 flex items-center justify-center">
              <Server size={18} className="text-blue" />
            </div>
            <div>
              <h1 className="text-lg font-bold">{asset.hostname || asset.ip_address}</h1>
              <div className="flex items-center gap-3 mt-0.5">
                <span className="font-mono text-xs text-mid">{asset.ip_address}</span>
                {asset.fqdn && asset.fqdn !== asset.hostname && (
                  <span className="font-mono text-xs text-dim">{asset.fqdn}</span>
                )}
                <span className="font-mono text-[10px] text-dim">
                  {asset.os_pretty || asset.os_name}
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {asset.is_stale && (
              <span className="badge bg-yellow/10 text-yellow border-yellow/20">STALE</span>
            )}
            <CritBadge c={asset.criticality} />
          </div>
        </div>
      </div>

      {/* Vuln summary strip */}
      {asset.vuln_summary && (
        <div className="grid grid-cols-5 gap-3">
          {[
            { label: 'Critical', value: asset.vuln_summary.CRITICAL, color: 'text-red',    bg: 'bg-red/5 border-red/20' },
            { label: 'High',     value: asset.vuln_summary.HIGH,     color: 'text-orange', bg: 'bg-orange/5 border-orange/20' },
            { label: 'Medium',   value: asset.vuln_summary.MEDIUM,   color: 'text-yellow', bg: 'bg-yellow/5 border-yellow/20' },
            { label: 'Low',      value: asset.vuln_summary.LOW,      color: 'text-green',  bg: 'bg-green/5 border-green/20' },
            { label: 'KEV',      value: asset.vuln_summary.kev,      color: 'text-red',    bg: 'bg-red/5 border-red/30' },
          ].map(({ label, value, color, bg }) => (
            <div key={label} className={`card border ${bg} text-center py-2`}>
              <div className={`text-2xl font-bold ${color}`}>{value}</div>
              <div className="text-[10px] text-dim mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-5">
        {/* Identity — editable fields */}
        <div className="card space-y-4">
          <h2 className="font-semibold text-sm flex items-center gap-2">
            <Server size={14} className="text-blue" /> Identity
          </h2>
          <EditableField
            label="System Owner"
            value={asset.system_owner}
            onSave={(v) => mutation.mutate({ system_owner: v })}
          />
          <EditableField
            label="FISMA Boundary"
            value={asset.fisma_boundary}
            onSave={(v) => mutation.mutate({ fisma_boundary: v })}
          />
          <EditableSelect
            label="Criticality"
            value={asset.criticality}
            options={['HIGH', 'MEDIUM', 'LOW']}
            onSave={(v) => mutation.mutate({ criticality: v })}
          />
          <InfoRow label="First Seen"   value={fmtDate(asset.first_seen)} />
          <InfoRow label="Last Seen"    value={fmtDate(asset.last_seen)} />
          <InfoRow label="Agent"        value={asset.agent_version || '—'} mono />
          <InfoRow label="Collected At" value={fmtDate(asset.collected_at)} />
        </div>

        {/* Hardware */}
        <div className="card space-y-3">
          <h2 className="font-semibold text-sm flex items-center gap-2">
            <Cpu size={14} className="text-purple" /> Hardware
          </h2>
          {asset.hardware && <>
            <InfoRow label="Manufacturer" value={asset.hardware.manufacturer} />
            <InfoRow label="Model"        value={asset.hardware.model} />
            <InfoRow label="Serial"       value={asset.hardware.serial_number} mono />
            <InfoRow label="CPU"          value={asset.hardware.cpu_model} />
            <InfoRow label="Cores"        value={asset.hardware.cpu_cores_logical} />
            <InfoRow label="RAM"          value={asset.hardware.ram_gb ? `${asset.hardware.ram_gb} GB` : null} />
            <InfoRow label="Architecture" value={asset.hardware.architecture} />
            <InfoRow label="BIOS"         value={asset.hardware.bios_version} mono />
            <InfoRow label="Virtual"
              value={asset.hardware.is_virtual
                ? (asset.hardware.virtualization_platform || 'Yes')
                : 'No (physical)'}
            />
          </>}
        </div>
      </div>

      {/* Network interfaces */}
      {asset.network_interfaces?.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-sm flex items-center gap-2 mb-3">
            <Network size={14} className="text-green" /> Network Interfaces
          </h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-border">
                {['Interface', 'MAC Address', 'IPv4'].map(h => (
                  <th key={h} className="font-mono text-[10px] text-dim uppercase tracking-wide pb-2 pr-6">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {asset.network_interfaces.map((iface, i) => (
                <tr key={i} className="border-b border-border/50">
                  <td className="py-2 pr-6 font-mono text-xs text-text">{iface.name}</td>
                  <td className="py-2 pr-6 font-mono text-xs text-mid">{iface.mac || '—'}</td>
                  <td className="py-2 font-mono text-xs text-mid">
                    {iface.ipv4?.join(', ') || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Software inventory */}
      {asset.software && (
        <div className="card">
          <h2 className="font-semibold text-sm flex items-center gap-2 mb-3">
            <Package size={14} className="text-yellow" /> Software Inventory
          </h2>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <Stat label="Total Packages"   value={asset.software.package_count} />
            <Stat label="EOL Packages"     value={asset.software.eol_package_count}
                  color={asset.software.eol_package_count > 0 ? 'text-red' : 'text-green'} />
            <Stat label="CPE Matched"      value={asset.software.cpe_matched_count} />
          </div>
          {asset.software.eol_packages?.length > 0 && (
            <div>
              <div className="text-xs text-dim mb-2">EOL Packages</div>
              <div className="flex flex-wrap gap-1.5">
                {asset.software.eol_packages.map((pkg, i) => (
                  <span key={i} className="font-mono text-[10px] bg-red/10 text-red border border-red/20 px-2 py-0.5 rounded">
                    {pkg}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Open vulnerabilities */}
      {asset.vulnerabilities?.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-sm flex items-center gap-2 mb-3">
            <ShieldAlert size={14} className="text-red" />
            Open Vulnerabilities ({asset.vulnerabilities.length})
          </h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-border">
                {['CVE ID', 'Severity', 'CVSS', 'KEV'].map(h => (
                  <th key={h} className="font-mono text-[10px] text-dim uppercase tracking-wide pb-2 pr-6">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {asset.vulnerabilities.map(v => (
                <tr key={v.id} className="border-b border-border/50 hover:bg-surface2/50">
                  <td className="py-2 pr-6 font-mono text-xs text-text">{v.cve_id}</td>
                  <td className="py-2 pr-6"><SevBadge s={v.severity} /></td>
                  <td className="py-2 pr-6 font-mono text-xs text-mid">{v.cvss_score ?? '—'}</td>
                  <td className="py-2">
                    {v.kev_member && (
                      <span className="flex items-center gap-1 text-red text-xs">
                        <AlertTriangle size={11} /> KEV
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

      {/* Additional Data -- catch-all for any new HostHarvest fields */}
      <AdditionalData tags={asset.tags} />

        </div>
      )}
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────────
function InfoRow({ label, value, mono }) {
  if (!value && value !== 0) return null
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="text-xs text-dim flex-shrink-0 w-32">{label}</span>
      <span className={`text-xs text-text text-right ${mono ? 'font-mono' : ''}`}>{value}</span>
    </div>
  )
}

function EditableField({ label, value, onSave }) {
  const [editing, setEditing] = useState(false)
  const [draft,   setDraft]   = useState(value || '')

  const save = () => { onSave(draft); setEditing(false) }
  const cancel = () => { setDraft(value || ''); setEditing(false) }

  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-xs text-dim flex-shrink-0 w-32">{label}</span>
      {editing ? (
        <div className="flex items-center gap-1 flex-1 justify-end">
          <input
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') save(); if (e.key === 'Escape') cancel() }}
            className="bg-surface2 border border-blue/40 rounded px-2 py-0.5 text-xs text-text outline-none w-full max-w-[180px]"
            autoFocus
          />
          <button onClick={save}   className="text-green hover:text-green/80"><Check size={13} /></button>
          <button onClick={cancel} className="text-dim hover:text-red"><X size={13} /></button>
        </div>
      ) : (
        <div className="flex items-center gap-1.5 group">
          <span className="text-xs text-text">{value || <span className="text-dim italic">Not set</span>}</span>
          <button
            onClick={() => setEditing(true)}
            className="opacity-0 group-hover:opacity-100 text-dim hover:text-blue transition-opacity"
          >
            <Edit2 size={11} />
          </button>
        </div>
      )}
    </div>
  )
}

function EditableSelect({ label, value, options, onSave }) {
  const [editing, setEditing] = useState(false)
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-xs text-dim flex-shrink-0 w-32">{label}</span>
      {editing ? (
        <select
          value={value}
          onChange={e => { onSave(e.target.value); setEditing(false) }}
          onBlur={() => setEditing(false)}
          className="bg-surface2 border border-blue/40 rounded px-2 py-0.5 text-xs text-text outline-none"
          autoFocus
        >
          {options.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : (
        <div className="flex items-center gap-1.5 group">
          <CritBadge c={value} />
          <button
            onClick={() => setEditing(true)}
            className="opacity-0 group-hover:opacity-100 text-dim hover:text-blue transition-opacity"
          >
            <Edit2 size={11} />
          </button>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, color = 'text-text' }) {
  return (
    <div className="bg-surface2 rounded-lg p-3 text-center">
      <div className={`text-2xl font-bold ${color}`}>{value ?? '—'}</div>
      <div className="text-[10px] text-dim mt-0.5">{label}</div>
    </div>
  )
}

function CritBadge({ c }) {
  const map = { HIGH: 'text-red border-red/20 bg-red/5', MEDIUM: 'text-yellow border-yellow/20 bg-yellow/5', LOW: 'text-green border-green/20 bg-green/5' }
  return <span className={`badge ${map[c] || ''}`}>{c}</span>
}

function SevBadge({ s }) {
  const map = { CRITICAL: 'badge-critical', HIGH: 'badge-high', MEDIUM: 'badge-medium', LOW: 'badge-low' }
  return <span className={`badge ${map[s] || ''}`}>{s}</span>
}

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// Keys already surfaced in named panels -- excluded from the catch-all
const KNOWN_TAG_KEYS = new Set([
  'architecture', 'cpu_model', 'cpu_cores_logical', 'cpu_cores_physical',
  'ram_gb', 'manufacturer', 'model', 'serial_number', 'is_virtual',
  'virtualization_platform', 'bios_version', 'collected_at',
  'package_count', 'eol_package_count', 'eol_packages', 'cpe_matched_count',
  'network_interfaces',
])

function AdditionalData({ tags }) {
  const [open, setOpen] = useState(false)

  const extras = Object.entries(tags || {}).filter(([k]) => !KNOWN_TAG_KEYS.has(k))
  if (!extras.length) return null

  return (
    <div className="card">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between text-left group"
      >
        <h2 className="font-semibold text-sm text-dim group-hover:text-text transition-colors">
          Additional Data
          <span className="font-mono text-[10px] text-dim/60 ml-2">
            {extras.length} field{extras.length !== 1 ? 's' : ''}
          </span>
        </h2>
        <ChevronDown
          size={15}
          className={`text-dim transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="mt-4 space-y-2 border-t border-border pt-4">
          {extras.map(([key, value]) => (
            <div key={key} className="flex items-start justify-between gap-4">
              <span className="font-mono text-[10px] text-dim flex-shrink-0 w-48 pt-0.5">
                {key}
              </span>
              <span className="text-xs text-mid text-right break-all">
                {renderValue(value)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function renderValue(value) {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean')  return value ? 'true' : 'false'
  if (typeof value === 'object')   return JSON.stringify(value)
  return String(value)
}
