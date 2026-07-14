import { useId } from 'react'
import { SearchSelect } from './SearchSelect.tsx'
import type { CatalogItem } from '../types/catalogs'
import type { EquipmentRow } from '../types/reports'
import { searchEquipment, listUnits } from '../api/catalogs.ts'

export interface EquipmentRowsProps {
  rows: EquipmentRow[]
  onChange: (rows: EquipmentRow[]) => void
}

const OWNERSHIP_OPTIONS: { value: EquipmentRow['ownership']; label: string }[] = [
  { value: 'own', label: 'Собственная' },
  { value: 'rented', label: 'Аренда' },
  { value: 'contractor', label: 'Подрядчик' },
]

export function EquipmentRows({ rows, onChange }: EquipmentRowsProps) {
  const baseId = useId()

  const updateRow = (index: number, patch: Partial<EquipmentRow>) => {
    const next = rows.map((row, i) => (i === index ? { ...row, ...patch } : row))
    onChange(next)
  }

  const addRow = () => {
    onChange([
      ...rows,
      {
        id: crypto.randomUUID(),
        equipment_type_id: null,
        ownership: 'own',
        unit_id: null,
        quantity: '',
        comment: '',
      },
    ])
  }

  const removeRow = (index: number) => {
    const next = rows.filter((_, i) => i !== index)
    onChange(next)
  }

  const handleTypeSelect = async (index: number, item: CatalogItem | null) => {
    let unitId: number | null = null
    if (item) {
      const units = await listUnits()
      const defaultUnit = units.items.find((u) => u.name === 'кубометр' || u.symbol === 'м³')
      unitId = defaultUnit?.id ?? null
    }
    updateRow(index, {
      equipment_type_id: item?.id ?? null,
      unit_id: unitId,
    })
  }

  return (
    <div className="equipment-rows" data-testid="equipment-rows">
      <div className="section-header">
        <span className="field-label">Техника</span>
        <button type="button" className="btn-add" onClick={addRow}>
          + Добавить
        </button>
      </div>
      {rows.length === 0 && <p className="placeholder">Нет строк техники</p>}
      {rows.map((row, index) => (
        <div key={row.id} className="row-card">
          <SearchSelect
            label="Тип техники"
            value={
              row.equipment_type_id
                ? { id: row.equipment_type_id, code: '', name: '' }
                : null
            }
            onChange={(item) => handleTypeSelect(index, item)}
            searchFn={(q) => searchEquipment(q).then((r) => r.items)}
            placeholder="Поиск техники..."
          />
          <div className="field">
            <label className="field-label">Принадлежность</label>
            <select
              className="field-input"
              value={row.ownership}
              onChange={(e) =>
                updateRow(index, { ownership: e.target.value as EquipmentRow['ownership'] })
              }
            >
              {OWNERSHIP_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor={`${baseId}-qty-${index}`} className="field-label">
              Количество
            </label>
            <input
              id={`${baseId}-qty-${index}`}
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
