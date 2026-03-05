import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const { login }           = useAuth()
  const navigate            = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/dashboard')
    } catch {
      setError('Invalid username or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bg flex flex-col">
      {/* Classification banner */}
      <div className="bg-[#1a2a00] border-b border-[#3a5a00] px-5 py-1 flex items-center justify-between">
        <span className="font-mono text-[10px] font-semibold text-[#7bc900] tracking-widest uppercase">
          Unclassified // CUI
        </span>
        <span className="text-[10px] text-[#4a6a20]">
          This system processes Controlled Unclassified Information
        </span>
      </div>

      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          {/* Logo */}
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue to-blue/60 flex items-center justify-center font-mono font-bold text-white">
              IF
            </div>
            <div>
              <div className="font-bold text-lg tracking-tight">IronFist</div>
              <div className="font-mono text-[10px] text-dim uppercase tracking-wider">
                Federal Vulnerability Management
              </div>
            </div>
          </div>

          {/* Gov notice */}
          <div className="bg-red/5 border border-red/20 rounded-lg p-3 mb-6 text-[11px] text-red/80 leading-relaxed">
            <strong className="text-red">U.S. GOVERNMENT SYSTEM NOTICE</strong><br />
            This system is for authorized users only. All activity is monitored
            and recorded. Unauthorized access is prohibited.
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-3">
            {error && (
              <div className="bg-red/10 border border-red/20 rounded-lg px-3 py-2 text-[11px] text-red">
                {error}
              </div>
            )}
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-surface2 border border-border2 rounded-lg px-4 py-2.5 text-sm text-text placeholder-dim outline-none focus:border-blue/50 transition-colors"
              autoComplete="off"
              required
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-surface2 border border-border2 rounded-lg px-4 py-2.5 text-sm text-text placeholder-dim outline-none focus:border-blue/50 transition-colors"
              required
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue hover:bg-blue/80 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition-colors text-sm"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div className="mt-4 flex items-center gap-2 justify-center text-[11px] text-dim">
            <span className="w-1.5 h-1.5 rounded-full bg-green inline-block" />
            TLS 1.3 · AES-256 at rest · Auth mode: local
          </div>

          {/* Dev badge */}
          <div className="mt-3 text-center">
            <span className="font-mono text-[9px] bg-yellow/5 border border-yellow/20 text-yellow px-2 py-0.5 rounded">
              DEV — local auth enabled
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
