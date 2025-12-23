import { Routes, Route, Navigate } from 'react-router-dom'
import DashboardLayout from './components/dashboard/DashboardLayout'
import Dashboard from './pages/Dashboard'
import Profiles from './pages/Profiles'
import Jobs from './pages/Jobs'
import Applications from './pages/Applications'
import Settings from './pages/Settings'

function App() {
  return (
    <Routes>
      <Route path="/" element={<DashboardLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="profiles" element={<Profiles />} />
        <Route path="jobs" element={<Jobs />} />
        <Route path="applications" element={<Applications />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}

export default App

