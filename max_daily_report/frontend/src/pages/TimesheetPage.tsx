import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchTimesheet, type TimesheetResponse, type TimesheetRow } from '../api/timesheet.ts'
import { searchObjects } from '../api/catalogs.ts'
import { ErrorState } from '../components/ErrorState.tsx'
import { Loading } from '../components/Loading.tsx'
import { SearchSelect } from '../components/SearchSelect.tsx'
import { useAuth } from '../hooks/useAuth.ts'
import type { CatalogItem } from '../types/catalogs'

function formatISODate(d: Date): string {
  return d.toISOString().split('T')[0]
}

function getDefaultRange(): { from: string; to: string } {
  const to = new Date()
  const from = new Date()
  from.setDate(to.getDate() - 13)
  return { from: formatISODate(from), to: formatISODate(to) }
}

export function TimesheetPage() {
  const { loading: authLoading, error: authError } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [objectId, setObjectId] = useState<number | null>(
    searchParams.get('object_id') ? Number(searchParams.get('object_id')) : null,
  )
  const { from: defaultFrom, to: defaultTo } = getDefaultRange()
  const [dateFrom, setDateFrom] = useState(searchParams.get('date_from') ?? defaultFrom)
  const [dateTo, setDateTo] = useState(searchParams.get('date_to') ?? defaultTo)
  const [data, setData] = useState<TimesheetResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const objectSearch = useCallback(
    (q: string) => searchObjects(q).then((r) => r.items),
    [],
  )

  useEffect(() => {
    if (!objectId) {
      setData(null)
      return
    }
    setLoading(true)
    setError(null)
    fetchTimesheet(objectId, dateFrom, dateTo)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false))
  }, [objectId, dateFrom, dateTo])

  const handleObjectChange = (id: number | null) => {
    setObjectId(id)
    if (id) {
      setSearchParams({ object_id: String(id), date_from: dateFrom, date_to: dateTo })
    }
  }

  const handleDateChange = (from: string, to: string) => {
    setDateFrom(from)
    setDateTo(to)
    if (objectId) {
      setSearchParams({ object_id: String(objectId), date_from: from, date_to: to })
    }
  }

  if (authLoading) return <Loading />
  if (authError) return <ErrorState message={authError} />

  return (
    <div className="timesheet-page">
      <h1>Табель</h1>

      <div className="timesheet-controls">
        <SearchSelect
          label="Объект"
          placeholder="Выберите объект"
          value={null}
          onChange={(item: CatalogItem | null) => handleObjectChange(item?.id ?? null)}
          searchFn={objectSearch}
        />
        <div className="date-range">
          <label>
            С
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => handleDateChange(e.target.value, dateTo)}
            />
          </label>
          <label>
            По
            <input
              type="date"
              value={dateTo}
              onChange={(e) => handleDateChange(dateFrom, e.target.value)}
            />
          </label>
        </div>
      </div>

      {!objectId && <p className="hint">Выберите объект и период</p>}
      {loading && <Loading />}
      {error && <ErrorState message={error} />}
      {data && !loading && (
        <TimesheetTable data={data} missingDays={new Set(data.missing_days)} />
      )}
    </div>
  )
}

function TimesheetTable({
  data,
  missingDays,
}: {
  data: TimesheetResponse
  missingDays: Set<string>
}) {
  const grouped = useMemo(() => {
    const byCategory: Record<string, TimesheetRow[]> = {}
    data.rows.forEach((row) => {
      byCategory[row.category] = byCategory[row.category] ?? []
      byCategory[row.category].push(row)
    })
    return byCategory
  }, [data.rows])

  const categoryTitle: Record<string, string> = {
    personnel: 'Персонал',
    soil: 'Вывоз грунта',
    equipment: 'Техника',
    work: 'Работы',
  }

  return (
    <div className="timesheet-table-wrapper">
      <table className="timesheet-table">
        <thead>
          <tr>
            <th className="sticky-col category-col">Категория</th>
            <th className="sticky-col item-col">Показатель</th>
            <th className="sticky-col unit-col">Ед.</th>
            {data.days.map((day) => (
              <th key={day} className={missingDays.has(day) ? 'missing-day' : ''}>
                {day.slice(5)}
              </th>
            ))}
            <th>Итог</th>
            <th>Средн</th>
            <th>Макс</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(grouped).map(([category, rows]) =>
            rows.map((row, idx) => (
              <tr key={`${category}-${row.item_name}-${row.unit}-${idx}`}>
                <td className="sticky-col category-col">
                  {idx === 0 ? categoryTitle[category] ?? category : ''}
                </td>
                <td className="sticky-col item-col">
                  {row.item_name}
                  {row.ownership_or_method ? ` (${row.ownership_or_method})` : ''}
                </td>
                <td className="sticky-col unit-col">{row.unit}</td>
                {row.values.map((value, dayIdx) => (
                  <td
                    key={dayIdx}
                    className={
                      value === '' && missingDays.has(data.days[dayIdx]) ? 'missing-cell' : ''
                    }
                  >
                    {value}
                  </td>
                ))}
                <td className="total-cell">{row.total}</td>
                <td>{row.average}</td>
                <td>{row.max}</td>
              </tr>
            )),
          )}
          {data.rows.length === 0 && (
            <tr>
              <td colSpan={data.days.length + 6} className="empty-cell">
                Нет данных за выбранный период
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
