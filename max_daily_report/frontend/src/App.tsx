import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout.tsx'
import { AdminCatalogsPage } from './pages/AdminCatalogsPage.tsx'
import { ReportPage } from './pages/ReportPage.tsx'
import { ReportsPage } from './pages/ReportsPage.tsx'
import { TimesheetPage } from './pages/TimesheetPage.tsx'
import { StatusPage } from './pages/StatusPage.tsx'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/report" replace />} />
        <Route path="/report" element={<ReportPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/timesheet" element={<TimesheetPage />} />
        <Route path="/status" element={<StatusPage />} />
        <Route path="/admin/catalogs" element={<AdminCatalogsPage />} />
      </Route>
    </Routes>
  )
}
