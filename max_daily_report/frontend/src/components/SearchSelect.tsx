import { useEffect, useId, useRef, useState } from 'react'
import { useDebounce } from '../hooks/useDebounce'
import type { CatalogItem } from '../types/catalogs'

export interface SearchSelectProps {
  label: string
  value: CatalogItem | null
  onChange: (item: CatalogItem | null) => void
  searchFn: (q: string) => Promise<CatalogItem[]>
  disabled?: boolean
  placeholder?: string
}

export function SearchSelect({
  label,
  value,
  onChange,
  searchFn,
  disabled,
  placeholder = 'Начните вводить...',
}: SearchSelectProps) {
  const id = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState(value ? `${value.name} (${value.code})` : '')
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [items, setItems] = useState<CatalogItem[]>([])
  const debouncedQuery = useDebounce(query, 300)

  useEffect(() => {
    if (!open) return
    if (debouncedQuery.trim().length > 0 && debouncedQuery.trim().length < 2) {
      setItems([])
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    searchFn(debouncedQuery)
      .then((results) => {
        setItems(results.slice(0, 20))
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Ошибка поиска')
      })
      .finally(() => setLoading(false))
  }, [debouncedQuery, open, searchFn])

  const handleSelect = (item: CatalogItem) => {
    onChange(item)
    setQuery(`${item.name} (${item.code})`)
    setOpen(false)
    inputRef.current?.blur()
  }

  const handleClear = () => {
    onChange(null)
    setQuery('')
    setItems([])
    setOpen(true)
    inputRef.current?.focus()
  }

  return (
    <div className="field" data-testid="search-select">
      <label htmlFor={id} className="field-label">{label}</label>
      <div className="search-select-input-wrap">
        <input
          ref={inputRef}
          id={id}
          type="text"
          className="field-input"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            if (!open) setOpen(true)
            if (value) onChange(null)
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete="off"
          aria-autocomplete="list"
          aria-expanded={open}
        />
        {value && (
          <button
            type="button"
            className="search-select-clear"
            onClick={handleClear}
            aria-label="Очистить"
          >
            ×
          </button>
        )}
      </div>
      {open && (
        <ul className="search-select-dropdown" role="listbox">
          {loading && <li className="search-select-state">Загрузка…</li>}
          {!loading && error && (
            <li className="search-select-state search-select-error" role="alert">{error}</li>
          )}
          {!loading && !error && items.length === 0 && (
            <li className="search-select-state">Нет результатов</li>
          )}
          {!loading &&
            !error &&
            items.map((item) => (
              <li key={item.id} role="option">
                <button
                  type="button"
                  className="search-select-option"
                  onMouseDown={(e) => {
                    e.preventDefault()
                    handleSelect(item)
                  }}
                >
                  <span className="search-select-option-name">{item.name}</span>
                  <span className="search-select-option-code">{item.code}</span>
                </button>
              </li>
            ))}
        </ul>
      )}
    </div>
  )
}
