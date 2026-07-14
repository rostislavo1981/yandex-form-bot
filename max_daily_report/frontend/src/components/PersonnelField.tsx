import type { StaffValues } from '../types/reports'

export interface PersonnelFieldProps {
  value: StaffValues
  onChange: (value: StaffValues) => void
}

const FIELDS: { key: keyof StaffValues; label: string }[] = [
  { key: 'itr', label: 'ИТР' },
  { key: 'internal', label: 'Штатные' },
  { key: 'external', label: 'Внештатные' },
]

export function PersonnelField({ value, onChange }: PersonnelFieldProps) {
  return (
    <div className="personnel-field" data-testid="personnel-field">
      <span className="field-label">Персонал</span>
      <div className="personnel-row">
        {FIELDS.map(({ key, label }) => (
          <div key={key} className="personnel-cell">
            <label htmlFor={`personnel-${key}`} className="field-label">
              {label}
            </label>
            <input
              id={`personnel-${key}`}
              type="number"
              min="0"
              step="1"
              className="field-input"
              value={value[key]}
              onChange={(e) =>
                onChange({
                  ...value,
                  [key]: Math.max(0, Number.parseInt(e.target.value || '0', 10)),
                })
              }
            />
          </div>
        ))}
      </div>
    </div>
  )
}
