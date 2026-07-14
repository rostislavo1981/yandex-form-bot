import { SearchSelect } from './SearchSelect.tsx'
import type { CatalogItem } from '../types/catalogs'
import type { WorkRow } from '../types/reports'
import { searchWorkTypes, searchWorkMethods, listUnits } from '../api/catalogs.ts'

export interface WorkRowsProps {
  rows: WorkRow[]
  onChange: (rows: WorkRow[]) => void
}

export function WorkRows({ rows, onChange }: WorkRowsProps) {
  const updateRow = (index: number, patch: Partial<WorkRow>) => {
    const next = rows.map((row, i) => (i === index ? { ...row, ...patch } : row))
    onChange(next)
  }

  const addRow = () => {
    onChange([
      ...rows,
      {
        id: crypto.randomUUID(),
        work_type_id: null,
        work_method_id: null,
        unit_id: null,
        quantity: '',
        comment: '',
      },
    ])
  }

  const removeRow = (index: number) => {
    onChange(rows.filter((_, i) => i !== index))
  }

  const handleTypeSelect = async (index: number, item: CatalogItem | null) => {
    let unitId: number | null = null
    if (item) {
      const units = await listUnits()
      const defaultUnit = units.items.find((u) => u.name === 'кубометр' || u.symbol === 'м³')
      unitId = defaultUnit?.id ?? null
    }
    updateRow(index, {
      work_type_id: item?.id ?? null,
      work_method_id: null,
      unit_id: unitId,
    })
  }

  return (
    <div className="work-rows" data-testid="work-rows">
      <div className="section-header">
        <span className="field-label">Работы</span>
        <button type="button" className="btn-add" onClick={addRow}>
          + Добавить
        </button>
      </div>
      {rows.length === 0 && <p className="placeholder">Нет строк работ</p>}
      {rows.map((row, index) => (
        <div key={row.id} className="row-card">
          <SearchSelect
            label="Вид работ"
            value={
              row.work_type_id
                ? { id: row.work_type_id, code: '', name: '' }
                : null
            }
            onChange={(item) => handleTypeSelect(index, item)}
            searchFn={(q) => searchWorkTypes(q).then((r) => r.items)}
            placeholder="Поиск вида работ..."
          />
          {row.work_type_id && (
            <SearchSelect
              label="Способ работ"
              value={
                row.work_method_id
                  ? { id: row.work_method_id, code: '', name: '' }
                  : null
              }
              onChange={(item) =>
                updateRow(index, { work_method_id: item?.id ?? null })
              }
              searchFn={(q) =>
                searchWorkMethods(row.work_type_id as number, q).then((r) => r.items)
              }
              placeholder="Поиск способа..."
            />
          )}
          <div className="field">
            <label className="field-label">Количество</label>
            <input
              type="number"
              min="0"
              step="0.01"
              className="field-input"
              value={row.quantity}
              onChange={(e) => updateRow(index, { quantity: e.target.value })}
              placeholder="0.00"
            />
          </div>
          <button type="button" className="btn-remove" onClick={() => removeRow(index)}>
            Удалить
          </button>
        </div>
      ))}
    </div>
  )
}
