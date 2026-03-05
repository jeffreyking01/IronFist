import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './context/AuthContext'
import LoginPage       from './pages/LoginPage'
import DashboardPage   from './pages/DashboardPage'
import AssetsPage      from './pages/AssetsPage'
import AssetDetailPage from './pages/AssetDetailPage'
import VulnsPage       from './pages/VulnsPage'
import KEVPage         from './pages/KEVPage'
import ConnectorsPage  from './pages/ConnectorsPage'
import Layout          from './components/Layout'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
})

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user)   return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>
              <Route index             element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard"  element={<DashboardPage />} />
              <Route path="assets"     element={<AssetsPage />} />
              <Route path="assets/:id" element={<AssetDetailPage />} />
              <Route path="vulns"      element={<VulnsPage />} />
              <Route path="kev"        element={<KEVPage />} />
              <Route path="connectors" element={<ConnectorsPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
