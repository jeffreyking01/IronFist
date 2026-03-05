import { createContext, useContext, useState, useEffect } from 'react'
import { authApi } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null)
  const [loading, setLoading] = useState(true)

  // Restore session from localStorage on mount
  useEffect(() => {
    const token = localStorage.getItem('ironfist_token')
    const saved = localStorage.getItem('ironfist_user')
    if (token && saved) {
      setUser(JSON.parse(saved))
    }
    setLoading(false)
  }, [])

  const login = async (username, password) => {
    const res  = await authApi.login(username, password)
    const data = res.data
    localStorage.setItem('ironfist_token', data.access_token)
    localStorage.setItem('ironfist_user', JSON.stringify({
      username: data.username,
      role:     data.role,
      authMode: data.auth_mode,
    }))
    setUser({ username: data.username, role: data.role, authMode: data.auth_mode })
    return data
  }

  const logout = () => {
    localStorage.removeItem('ironfist_token')
    localStorage.removeItem('ironfist_user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
