import { useState, useEffect } from 'react'
import { api } from '../api/client'

interface MissingItem {
  responsible: string
  object_code: string
}

interface SubmissionStatus {
  expected: number
  submitted: number
  late: number
  pending: number
  missing: MissingItem[]
}

export function StatusPage() {
  const [status, setStatus] = useState<SubmissionStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadStatus()
  }, [])

  async function loadStatus() {
    setLoading(true)
    setError(null)
    try {
      const today = new Date().toISOString().split('T')[0]
      const data = await api.get<SubmissionStatus>(
        `/api/submission-status?target_date=${today}`
      )
      setStatus(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка загрузки')
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="screen"><p>Загрузка...</p></div>
  if (error) return <div className="screen"><p className="error">{error}</p></div>
  if (!status) return <div className="screen"><p>Нет данных</p></div>

  return (
    <div className="screen">
      <h1>Статус сдачи</h1>
      <div className="status-summary">
        <div className="status-item">
          <span className="status-label">Ожидается</span>
          <span className="status-value">{status.expected}</span>
        </div>
        <div className="status-item">
          <span className="status-label">Сдано</span>
          <span className="status-value status-ok">{status.submitted}</span>
        </div>
        <div className="status-item">
          <span className="status-label">С опозданием</span>
          <span className="status-value status-late">{status.late}</span>
        </div>
        <div className="status-item">
          <span className="status-label">Не сдано</span>
          <span className="status-value status-pending">{status.pending}</span>
        </div>
      </div>
      {status.missing.length > 0 && (
        <div className="missing-list">
          <h2>Не сдали:</h2>
          <ul>
            {status.missing.map((item, idx) => (
              <li key={idx}>
                {item.responsible} — {item.object_code}
              </li>
            ))}
          </ul>
        </div>
      )}
      <button onClick={loadStatus} className="refresh-btn">
        Обновить
      </button>
    </div>
  )
}
