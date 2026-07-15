import { useState, useEffect } from 'react'
import { api } from '../api/client'

interface ReportItem {
  id: number
  report_date: string
  object_id: number
  stage_id: number
  staff_itr: number
  staff_internal: number
  staff_external: number
  soil_export_m3: number | null
  status: string
  equipment: Array<{
    equipment_name_snapshot: string
    unit_name_snapshot: string
    quantity: number
  }>
  works: Array<{
    work_name_snapshot: string
    unit_name_snapshot: string
    quantity: number
  }>
}

interface ReportsResponse {
  items: ReportItem[]
  total: number
}

export function ReportsPage() {
  const [reports, setReports] = useState<ReportItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(0)
  const limit = 20

  useEffect(() => {
    loadReports()
  }, [page])

  async function loadReports() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<ReportsResponse>(
        `/api/reports?limit=${limit}&offset=${page * limit}`
      )
      setReports(data.items)
      setTotal(data.total)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка загрузки')
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="screen"><p>Загрузка...</p></div>
  if (error) return <div className="screen"><p className="error">{error}</p></div>

  const totalPages = Math.ceil(total / limit)

  return (
    <div className="screen">
      <h1>Отчёты</h1>
      <p className="total">Всего: {total}</p>
      {reports.length === 0 ? (
        <p className="placeholder">Нет отчётов</p>
      ) : (
        <div className="report-list">
          {reports.map((report) => (
            <div key={report.id} className="report-card">
              <div className="report-header">
                <span className="report-date">{report.report_date}</span>
                <span className={`report-status status-${report.status}`}>
                  {report.status === 'submitted' ? '✅' : '⏰'}
                </span>
              </div>
              <div className="report-details">
                {report.staff_itr > 0 && <span>ИТР: {report.staff_itr}</span>}
                {report.staff_internal > 0 && <span>Штат: {report.staff_internal}</span>}
                {report.staff_external > 0 && <span>Внеш: {report.staff_external}</span>}
                {report.soil_export_m3 && <span>Грунт: {report.soil_export_m3} м³</span>}
              </div>
              {report.equipment.length > 0 && (
                <div className="report-equipment">
                  Техника: {report.equipment.map(e =>
                    `${e.equipment_name_snapshot} ${e.quantity} ${e.unit_name_snapshot}`
                  ).join(', ')}
                </div>
              )}
              {report.works.length > 0 && (
                <div className="report-works">
                  Работы: {report.works.map(w =>
                    `${w.work_name_snapshot} ${w.quantity} ${w.unit_name_snapshot}`
                  ).join(', ')}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      {totalPages > 1 && (
        <div className="pagination">
          <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}>
            Назад
          </button>
          <span>{page + 1} / {totalPages}</span>
          <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}>
            Вперёд
          </button>
        </div>
      )}
    </div>
  )
}
