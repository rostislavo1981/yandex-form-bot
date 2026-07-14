import { useCallback, useMemo, useState } from 'react'
import { SearchSelect } from '../components/SearchSelect.tsx'
import { EquipmentRows } from '../components/EquipmentRows.tsx'
import { PersonnelField } from '../components/PersonnelField.tsx'
import { searchObjects, searchStages } from '../api/catalogs.ts'
import type { CatalogItem } from '../types/catalogs'
import type { EquipmentRow, ReportFormData, StaffValues } from '../types/reports'

const INITIAL_STAFF: StaffValues = { itr: 0, internal: 0, external: 0 }

export function ReportPage() {
  const [object, setObject] = useState<CatalogItem | null>(null)
  const [stage, setStage] = useState<CatalogItem | null>(null)
  const [reportDate, setReportDate] = useState(() => {
    const today = new Date()
    return today.toISOString().split('T')[0]
  })
  const [staff, setStaff] = useState<StaffValues>(INITIAL_STAFF)
  const [equipment, setEquipment] = useState<EquipmentRow[]>([])
  const [soilExport, setSoilExport] = useState('')
  const [comment, setComment] = useState('')

  const handleObjectChange = useCallback((item: CatalogItem | null) => {
    setObject(item)
    setStage(null)
  }, [])

  const stageSearch = useMemo(() => {
    if (!object) return null
    return (q: string) => searchStages(object.id, q).then((r) => r.items)
  }, [object])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const payload: ReportFormData = {
      report_date: reportDate,
      object_id: object?.id ?? null,
      stage_id: stage?.id ?? null,
      contractor_id: null,
      staff,
      soil_export_m3: soilExport,
      equipment,
      works: [],
      comment,
    }
    // eslint-disable-next-line no-console
    console.log('submit', payload)
  }

  return (
    <div className="screen report-page">
      <h1>Новый отчёт</h1>
      <form className="report-form" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="report-date" className="field-label">
            Дата
          </label>
          <input
            id="report-date"
            type="date"
            className="field-input"
            value={reportDate}
            onChange={(e) => setReportDate(e.target.value)}
          />
        </div>

        <SearchSelect
          label="Объект"
          value={object}
          onChange={handleObjectChange}
          searchFn={useCallback((q) => searchObjects(q).then((r) => r.items), [])}
          placeholder="Поиск объекта..."
        />

        {stageSearch && (
          <SearchSelect
            label="Этап"
            value={stage}
            onChange={setStage}
            searchFn={stageSearch}
            disabled={!object}
            placeholder="Поиск этапа..."
          />
        )}

        <PersonnelField value={staff} onChange={setStaff} />

        <EquipmentRows rows={equipment} onChange={setEquipment} />

        <div className="field">
          <label htmlFor="soil-export" className="field-label">
            Вывоз грунта, м³
          </label>
          <input
            id="soil-export"
            type="number"
            min="0"
            step="0.01"
            className="field-input"
            value={soilExport}
            onChange={(e) => setSoilExport(e.target.value)}
            placeholder="0.00"
          />
        </div>

        <div className="field">
          <label htmlFor="comment" className="field-label">
            Комментарий
          </label>
          <textarea
            id="comment"
            className="field-input"
            rows={3}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
        </div>

        <button type="submit" className="btn-primary">
          Отправить
        </button>
      </form>
    </div>
  )
}
