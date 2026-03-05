import { Outlet, NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  LayoutDashboard, Server, ShieldAlert,
  AlertTriangle, Plug, LogOut, RefreshCw
} from 'lucide-react'
import { useState } from 'react'
import { syncApi } from '../api/client'

const navItems = [
  { to: '/dashboard',  icon: LayoutDashboard, label: 'Dashboard'   },
  { to: '/kev',        icon: AlertTriangle,   label: 'KEV Watch'   },
  { to: '/vulns',      icon: ShieldAlert,     label: 'Vulnerabilities' },
  { to: '/assets',     icon: Server,          label: 'Assets'      },
  { to: '/connectors', icon: Plug,            label: 'Connectors'  },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const [syncing, setSyncing] = useState(false)

  const handleSync = async () => {
    setSyncing(true)
    try { await syncApi.all() } finally {
      setTimeout(() => setSyncing(false), 2000)
    }
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Classification banner */}
      <div className="bg-[#1a2a00] border-b border-[#3a5a00] px-5 py-1 flex items-center justify-between flex-shrink-0">
        <span className="font-mono text-[10px] font-semibold text-[#7bc900] tracking-widest uppercase">
          Unclassified // CUI
        </span>
        <span className="text-[10px] text-[#4a6a20]">
          This system processes Controlled Unclassified Information
        </span>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-52 bg-surface border-r border-border flex flex-col flex-shrink-0">
          {/* Logo */}
          <div className="px-5 py-4 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue to-blue/60 flex items-center justify-center font-mono font-bold text-white text-sm">
                IF
              </div>
              <div>
                <div className="font-bold text-sm tracking-tight">IronFist</div>
                <div className="font-mono text-[9px] text-dim uppercase tracking-wider">VulnMgmt Platform</div>
              </div>
            </div>
          </div>

          {/* Nav */}
          <nav className="flex-1 px-3 py-4 space-y-1">
            {navItems.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                    isActive
                      ? 'bg-blue/10 text-blue border border-blue/20'
                      : 'text-mid hover:text-text hover:bg-surface2'
                  }`
                }
              >
                <Icon size={15} />
                {label}
              </NavLink>
            ))}
          </nav>

          {/* Footer */}
          <div className="px-3 py-3 border-t border-border space-y-1">
            <button
              onClick={handleSync}
              disabled={syncing}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-mid hover:text-text hover:bg-surface2 transition-colors"
            >
              <RefreshCw size={15} className={syncing ? 'animate-spin' : ''} />
              {syncing ? 'Syncing...' : 'Sync All'}
            </button>
            <button
              onClick={logout}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-mid hover:text-red hover:bg-red/5 transition-colors"
            >
              <LogOut size={15} />
              Sign Out
            </button>
            <div className="px-3 pt-1">
              <div className="font-mono text-[10px] text-dim truncate">{user?.username}</div>
              <div className="font-mono text-[9px] text-dim/60 uppercase">{user?.role}</div>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-auto bg-bg p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
