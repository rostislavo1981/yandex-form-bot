import { useCallback, useMemo, useState } from 'react'
import { SearchSelect } from '../components/SearchSelect.tsx'
import { EquipmentRows } from '../components/EquipmentRows.tsx'
import { PersonnelField } from '../components/PersonnelField.tsx'
import { WorkRows } from '../components/WorkRows.tsx'
import { searchObjects, searchStages } from '../api/catalogs.ts'
import { submitReport } from '../api/reports.ts'
import type { CatalogItem, ContractRef, ObjectItem } from '../types/catalogs'
import type {
  EquipmentRow,
  ReportFormData,
  StaffValues,
  WorkRow,
} from '../types/reports'

const INITIAL_STAFF: StaffValues = { itr: 0, internal: 0, external: 0 }

function toNumber(value: string): string | null {
  const n = Number.parseFloat(value)
  return Number.isFinite(n) && n > 0 ? n.toFixed(2) : null
}

function cleanRows(rows: EquipmentRow[] | WorkRow[]): unknown[] {
  return rows
    .filter((row) => {
      const q = 'quantity' in row ? toNumber(row.quantity) : null
      return q !== null
    })
    .map((row) => ({
      ...row,
      quantity: toNumber(row.quantity),
    }))
}

export function ReportPage() {
  const [object, setObject] = useState<ObjectItem | null>(null)
  const [contract, setContract] = useState<ContractRef | null>(null)
  const [stage, setStage] = useState<CatalogItem | null>(null)
  const [reportDate, setReportDate] = useState(() => {
    const today = new Date()
    return today.toISOString().split('T')[0]
  })
  const [staff, setStaff] = useState<StaffValues>(INITIAL_STAFF)
  const [equipment, setEquipment] = useState<EquipmentRow[]>([])
  const [works, setWorks] = useState<WorkRow[]>([])
  const [soilExport, setSoilExport] = useState('')
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<{ id: number; late: boolean } | null>(null)

  const handleObjectChange = useCallback((item: ObjectItem | null) => {
    setObject(item)
    setStage(null)
    if (item && item.contracts.length === 1) {
      setContract(item.contracts[0])
    } else {
      setContract(null)
    }
  }, [])

  const stageSearch = useMemo(() => {
    if (!object) return null
    return (q: string) => searchStages(object.id, q).then((r) => r.items)
  }, [object])

  const objectSearch = useCallback((q: string) => searchObjects(q).then((r) => r.items), [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!object || !stage) {
      setError('Выберите объект и этап')
      return
    }
    setSubmitting(true)
    setError(null)
    setSuccess(null)

    const payload: ReportFormData = {
      report_date: reportDate,
      object_id: object.id,
      stage_id: stage.id,
      contractor_id: null,
      contract_id: contract?.id ?? null,
      staff,
      soil_export_m3: soilExport ? toNumber(soilExport) : null,
      equipment: cleanRows(equipment) as EquipmentRow[],
      works: cleanRows(works) as WorkRow[],
      comment,
    }

    const idempotencyKey = crypto.randomUUID()
    try {
      const result = await submitReport(payload, idempotencyKey)
      setSuccess({ id: result.id, late: result.late })
      setEquipment([])
      setWorks([])
      setSoilExport('')
      setComment('')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Ошибка отправки'
      setError(message)
    } finally {
      setSubmitting(false)
    }
  }

  if (success) {
    return (
      <div className="screen report-page">
        <h1>Отчёт отправлен</h1>
        <p className="report-summary">
          Номер отчёта: {success.id}
          {success.late && <span className="badge-late">Опоздание</span>}
        </p>
        <button
          type="button"
          className="btn-primary"
          onClick={() => {
            setSuccess(null)
            setObject(null)
            setStage(null)
          }}
        >
          Заполнить ещё
        </button>
      </div>
    )
  }

  return (
    <div className="screen report-page">
      <h1>Новый отчёт</h1>
      <form className="report-form" onSubmit={handleSubmit}>
        {error && <div className="form-error" role="alert">{error}</div>}

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
          searchFn={objectSearch}
          placeholder="Поиск объекта..."
        />

        {object && (
          <div className="field">
            <label className="field-label">Полное название</label>
            <div className="field-input-readonly">
              {object.contracts?.[0]?.full_name || object.name}
            </div>
          </div>
        )}

        {object && object.contracts.length > 1 && (
          <div className="field">
            <label htmlFor="contract" className="field-label">
              Договор / официальный объект
            </label>
            <select
              id="contract"
              className="field-input"
              value={contract?.id ?? ''}
              onChange={(e) => {
                const selected =
                  object.contracts.find((c) => c.id === Number(e.target.value)) || null
                setContract(selected)
              }}
            >
              <option value="">Выберите договор</option>
              {object.contracts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} — {c.full_name}
                </option>
              ))}
            </select>
          </div>
        )}

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

        <WorkRows rows={works} onChange={setWorks} />

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

        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? 'Отправка…' : 'Отправить'}
        </button>
      </form>
    </div>
  )
}
