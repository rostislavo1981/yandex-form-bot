import { useCallback, useEffect, useState } from 'react'
import type { JSX } from 'react'
import { useAuth } from '../hooks/useAuth'
import { ErrorState } from '../components/ErrorState'
import { Loading } from '../components/Loading'
import * as api from '../api/admin'
import type {
  AdminAssignment,
  AdminCatalogItem,
  AdminEquipment,
  AdminObject,
  AdminObjectStage,
  AdminUnit,
  AdminUser,
  AdminWorkType,
  AdminWorkTypeMethod,
  CatalogTab,
} from '../types/admin'

const TABS: { key: CatalogTab; label: string }[] = [
  { key: 'objects', label: 'Объекты' },
  { key: 'stages', label: 'Этапы' },
  { key: 'contractors', label: 'Подрядчики' },
  { key: 'units', label: 'Единицы' },
  { key: 'equipment', label: 'Техника' },
  { key: 'work-types', label: 'Виды работ' },
  { key: 'work-methods', label: 'Способы работ' },
  { key: 'object-stages', label: 'Этапы объектов' },
  { key: 'work-type-methods', label: 'Способы видов работ' },
  { key: 'assignments', label: 'Назначения' },
  { key: 'users', label: 'Пользователи' },
]

type EditableRow = Record<string, unknown>

interface CatalogOptions {
  objects: AdminObject[]
  stages: AdminCatalogItem[]
  contractors: AdminCatalogItem[]
  units: AdminUnit[]
  workTypes: AdminWorkType[]
  workMethods: AdminCatalogItem[]
  users: AdminUser[]
}

const EMPTY_OPTIONS: CatalogOptions = {
  objects: [],
  stages: [],
  contractors: [],
  units: [],
  workTypes: [],
  workMethods: [],
  users: [],
}

export function AdminCatalogsPage() {
  const { user, loading: authLoading, error: authError } = useAuth()
  const [activeTab, setActiveTab] = useState<CatalogTab>('objects')
  const [items, setItems] = useState<unknown[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | 'new' | null>(null)
  const [editForm, setEditForm] = useState<EditableRow>({})
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importResult, setImportResult] = useState<string | null>(null)
  const [options, setOptions] = useState<CatalogOptions>(EMPTY_OPTIONS)

  const isManager = user?.role === 'manager' || user?.role === 'admin'

  const load = useCallback(async () => {
    if (!isManager) return
    setLoading(true)
    setError(null)
    try {
      let data: unknown[] = []
      switch (activeTab) {
        case 'objects':
          data = await api.listObjects()
          break
        case 'stages':
          data = await api.listStages()
          break
        case 'contractors':
          data = await api.listContractors()
          break
        case 'units':
          data = await api.listUnits()
          break
        case 'equipment':
          data = await api.listEquipment()
          break
        case 'work-types':
          data = await api.listWorkTypes()
          break
        case 'work-methods':
          data = await api.listWorkMethods()
          break
        case 'object-stages':
          data = await api.listObjectStages()
          break
        case 'work-type-methods':
          data = await api.listWorkTypeMethods()
          break
        case 'assignments':
          data = await api.listAssignments()
          break
        case 'users':
          data = await api.listAdminUsers()
          break
      }
      setItems(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки')
    } finally {
      setLoading(false)
    }
  }, [activeTab, isManager])

  useEffect(() => {
    setEditingId(null)
    setEditForm({})
    setImportResult(null)
    void load()
  }, [load])

  useEffect(() => {
    if (!isManager) return
    let cancelled = false
    async function loadOptions() {
      try {
        const [objects, stages, contractors, units, workTypes, workMethods, users] =
          await Promise.all([
            api.listObjects(),
            api.listStages(),
            api.listContractors(),
            api.listUnits(),
            api.listWorkTypes(),
            api.listWorkMethods(),
            api.listAdminUsers(),
          ])
        if (!cancelled) {
          setOptions({ objects, stages, contractors, units, workTypes, workMethods, users })
        }
      } catch {
        //Hints are best-effort; the active tab loader reports real errors.
      }
    }
    void loadOptions()
    return () => {
      cancelled = true
    }
  }, [isManager])

  const handleAdd = () => {
    setEditingId('new')
    setEditForm(defaultForm(activeTab))
  }

  const handleEdit = (row: unknown) => {
    setEditingId((row as { id: number }).id)
    setEditForm({ ...(row as object) })
  }

  const handleCancel = () => {
    setEditingId(null)
    setEditForm({})
  }

  const handleSave = async () => {
    setError(null)
    try {
      switch (activeTab) {
        case 'objects': {
          const data = editForm as unknown as AdminObject
          const payload = {
            code: data.code || '',
            name: data.name || '',
            short_title: data.short_title || null,
            full_title: data.full_title || null,
            active: data.active ?? true,
            sort_order: data.sort_order ?? null,
            execution_method: data.execution_method || null,
            default_contractor_id: data.default_contractor_id ?? null,
          }
          if (editingId === 'new') {
            await api.createObject(payload)
          } else {
            await api.updateObject(editingId as number, payload)
          }
          break
        }
        case 'stages':
        case 'contractors':
        case 'work-methods': {
          const data = editForm as unknown as AdminCatalogItem
          const payload = {
            code: data.code || '',
            name: data.name || '',
            active: data.active ?? true,
            sort_order: data.sort_order ?? null,
          }
          if (activeTab === 'stages') {
            if (editingId === 'new') {
              await api.createStage(payload)
            } else {
              await api.updateStage(editingId as number, payload)
            }
          } else if (activeTab === 'contractors') {
            if (editingId === 'new') {
              await api.createContractor(payload)
            } else {
              await api.updateContractor(editingId as number, payload)
            }
          } else {
            if (editingId === 'new') {
              await api.createWorkMethod(payload)
            } else {
              await api.updateWorkMethod(editingId as number, payload)
            }
          }
          break
        }
        case 'units': {
          const data = editForm as unknown as AdminUnit
          const payload = {
            code: data.code || '',
            name: data.name || '',
            symbol: data.symbol || '',
            active: data.active ?? true,
            sort_order: data.sort_order ?? null,
          }
          if (editingId === 'new') {
            await api.createUnit(payload)
          } else {
            await api.updateUnit(editingId as number, payload)
          }
          break
        }
        case 'equipment': {
          const data = editForm as unknown as AdminEquipment
          const payload = {
            code: data.code || '',
            name: data.name || '',
            default_unit_id: data.default_unit_id ?? null,
            active: data.active ?? true,
            sort_order: data.sort_order ?? null,
          }
          if (editingId === 'new') {
            await api.createEquipment(payload)
          } else {
            await api.updateEquipment(editingId as number, payload)
          }
          break
        }
        case 'work-types': {
          const data = editForm as unknown as AdminWorkType
          const payload = {
            code: data.code || '',
            name: data.name || '',
            default_unit_id: data.default_unit_id ?? null,
            active: data.active ?? true,
            sort_order: data.sort_order ?? null,
          }
          if (editingId === 'new') {
            await api.createWorkType(payload)
          } else {
            await api.updateWorkType(editingId as number, payload)
          }
          break
        }
        case 'object-stages': {
          const data = editForm as unknown as unknown as AdminObjectStage
          await api.createObjectStage({
            object_id: data.object_id || 0,
            stage_id: data.stage_id || 0,
            active: data.active ?? true,
          })
          break
        }
        case 'work-type-methods': {
          const data = editForm as unknown as unknown as AdminWorkTypeMethod
          await api.createWorkTypeMethod({
            work_type_id: data.work_type_id || 0,
            work_method_id: data.work_method_id || 0,
            active: data.active ?? true,
          })
          break
        }
        case 'assignments': {
          const data = editForm as unknown as AdminAssignment
          await api.createAssignment({
            user_id: data.user_id || 0,
            object_id: data.object_id || 0,
            active_from: data.active_from || '',
            active_to: data.active_to || '',
            schedule_type: data.schedule_type || 'daily',
            active: data.active ?? true,
          })
          break
        }
        case 'users': {
          const data = editForm as unknown as AdminUser
          const payload = {
            max_user_id: data.max_user_id || '',
            full_name: data.full_name || '',
            role: data.role || 'responsible',
            active: data.active ?? true,
          }
          if (editingId === 'new') {
            await api.createUser(payload)
          } else {
            await api.updateUser(editingId as number, payload)
          }
          break
        }
      }
      setEditingId(null)
      setEditForm({})
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка сохранения')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить запись?')) return
    setError(null)
    try {
      switch (activeTab) {
        case 'objects':
          await api.deleteObject(id)
          break
        case 'stages':
          await api.deleteStage(id)
          break
        case 'contractors':
          await api.deleteContractor(id)
          break
        case 'units':
          await api.deleteUnit(id)
          break
        case 'equipment':
          await api.deleteEquipment(id)
          break
        case 'work-types':
          await api.deleteWorkType(id)
          break
        case 'work-methods':
          await api.deleteWorkMethod(id)
          break
        case 'object-stages':
          await api.deleteObjectStage(id)
          break
        case 'work-type-methods':
          await api.deleteWorkTypeMethod(id)
          break
        case 'assignments':
          await api.deleteAssignment(id)
          break
        case 'users':
          await api.deleteUser(id)
          break
      }
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка удаления')
    }
  }

  const handleExport = async () => {
    setError(null)
    try {
      await api.exportCatalogs()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка экспорта')
    }
  }

  const handleTemplate = async () => {
    setError(null)
    try {
      await api.downloadTemplate()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки шаблона')
    }
  }

  const handleImport = async () => {
    if (!importFile) return
    setError(null)
    setImportResult(null)
    try {
      const result = (await api.importCatalogs(importFile)) as { id?: number; status?: string }
      setImportResult(`Импорт выполнен: id=${result.id}, status=${result.status}`)
      setImportFile(null)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка импорта')
    }
  }

  if (authLoading) return <Loading />
  if (authError) return <ErrorState message={authError} />
  if (!isManager) return <ErrorState message="Доступ только для менеджера или администратора" />

  return (
    <div className="screen admin-page">
      <h1>Справочники</h1>

      <div className="admin-toolbar">
        <button type="button" className="btn-add" onClick={handleExport}>
          Экспорт Excel
        </button>
        <button type="button" className="btn-add" onClick={handleTemplate}>
          Шаблон Excel
        </button>
        <label className="import-label">
          <input
            type="file"
            accept=".xlsx"
            onChange={(e) => setImportFile(e.target.files?.[0] ?? null)}
          />
          <button type="button" className="btn-primary" onClick={handleImport} disabled={!importFile}>
            Импорт
          </button>
        </label>
      </div>

      {importResult && <div className="admin-message success">{importResult}</div>}
      {error && <div className="form-error">{error}</div>}

      <div className="admin-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={activeTab === tab.key ? 'admin-tab active' : 'admin-tab'}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="admin-table-wrap">
        {loading ? (
          <Loading />
        ) : (
          <>
            <button type="button" className="btn-add" onClick={handleAdd}>
              + Добавить
            </button>
            <table className="admin-table">
              <thead>
                <tr>{columnsForTab(activeTab).map((col) => (
                  <th key={col.key}>{col.label}</th>
                ))}
                <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {editingId === 'new' && renderEditRow(activeTab, editForm, setEditForm, options)}
                {items.map((row) => {
                  const id = (row as { id: number }).id
                  const isEditing = editingId === id
                  return (
                    <tr key={id} className={isEditing ? 'editing' : ''}>
                      {isEditing
                        ? renderEditRow(activeTab, editForm, setEditForm, options)
                        : renderViewRow(activeTab, row as Record<string, unknown>)}
                      <td className="actions">
                        {isEditing ? (
                          <>
                            <button type="button" className="btn-primary" onClick={handleSave}>
                              Сохранить
                            </button>
                            <button type="button" className="btn-add" onClick={handleCancel}>
                              Отмена
                            </button>
                          </>
                        ) : (
                          <>
                            <button type="button" className="btn-add" onClick={() => handleEdit(row)}>
                              Редактировать
                            </button>
                            <button type="button" className="btn-remove" onClick={() => handleDelete(id)}>
                              Удалить
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  )
}

function defaultForm(tab: CatalogTab): EditableRow {
  switch (tab) {
    case 'objects':
      return { code: '', name: '', short_title: null, full_title: null, active: true, sort_order: null, execution_method: 'own', default_contractor_id: null }
    case 'units':
      return { code: '', name: '', symbol: '', active: true, sort_order: null }
    case 'equipment':
    case 'work-types':
      return { code: '', name: '', active: true, sort_order: null, default_unit_id: null }
    case 'object-stages':
      return { object_id: 0, stage_id: 0, active: true }
    case 'work-type-methods':
      return { work_type_id: 0, work_method_id: 0, active: true }
    case 'assignments':
      return { user_id: 0, object_id: 0, active_from: '', active_to: '', schedule_type: 'daily', active: true }
    case 'users':
      return { max_user_id: '', full_name: '', role: 'responsible', active: true }
    default:
      return { code: '', name: '', active: true, sort_order: null }
  }
}

interface ColumnDef {
  key: string
  label: string
}

function columnsForTab(tab: CatalogTab): ColumnDef[] {
  switch (tab) {
    case 'objects':
      return [
        { key: 'code', label: 'Код' },
        { key: 'name', label: 'Название' },
        { key: 'execution_method', label: 'Способ' },
        { key: 'default_contractor_id', label: 'Подрядчик ID' },
        { key: 'active', label: 'Активен' },
        { key: 'sort_order', label: 'Порядок' },
      ]
    case 'units':
      return [
        { key: 'code', label: 'Код' },
        { key: 'name', label: 'Название' },
        { key: 'symbol', label: 'Обозначение' },
        { key: 'active', label: 'Активен' },
        { key: 'sort_order', label: 'Порядок' },
      ]
    case 'equipment':
    case 'work-types':
      return [
        { key: 'code', label: 'Код' },
        { key: 'name', label: 'Название' },
        { key: 'default_unit_id', label: 'Единица по умолчанию ID' },
        { key: 'active', label: 'Активен' },
        { key: 'sort_order', label: 'Порядок' },
      ]
    case 'object-stages':
      return [
        { key: 'object_code', label: 'Объект' },
        { key: 'stage_code', label: 'Этап' },
        { key: 'active', label: 'Активна' },
      ]
    case 'work-type-methods':
      return [
        { key: 'work_type_code', label: 'Вид работы' },
        { key: 'work_method_code', label: 'Способ' },
        { key: 'active', label: 'Активна' },
      ]
    case 'assignments':
      return [
        { key: 'user_name', label: 'Пользователь' },
        { key: 'object_code', label: 'Объект' },
        { key: 'active_from', label: 'С' },
        { key: 'active_to', label: 'По' },
        { key: 'schedule_type', label: 'Расписание' },
        { key: 'active', label: 'Активно' },
      ]
    case 'users':
      return [
        { key: 'max_user_id', label: 'MAX ID' },
        { key: 'full_name', label: 'ФИО' },
        { key: 'role', label: 'Роль' },
        { key: 'active', label: 'Активен' },
      ]
    default:
      return [
        { key: 'code', label: 'Код' },
        { key: 'name', label: 'Название' },
        { key: 'active', label: 'Активен' },
        { key: 'sort_order', label: 'Порядок' },
      ]
  }
}

function renderViewRow(tab: CatalogTab, row: Record<string, unknown>): JSX.Element {
  const cols = columnsForTab(tab)
  return (
    <>
      {cols.map((col) => {
        const value = row[col.key]
        return (
          <td key={col.key}>
            {typeof value === 'boolean' ? (value ? 'Да' : 'Нет') : String(value ?? '')}
          </td>
        )
      })}
    </>
  )
}

function renderEditRow(
  tab: CatalogTab,
  form: EditableRow,
  setForm: (value: EditableRow) => void,
  options: CatalogOptions,
): JSX.Element {
  const update = (patch: EditableRow) => setForm({ ...form, ...patch })

  const textField = (key: string, placeholder: string, type = 'text') => (
    <input
      type={type}
      value={String((form[key] as string | number | boolean | undefined) ?? '')}
      placeholder={placeholder}
      onChange={(e) => update({ [key]: type === 'number' ? Number(e.target.value) : e.target.value })}
    />
  )

  const boolField = (key: string) => (
    <select
      value={String((form[key] as boolean | undefined) ?? true)}
      onChange={(e) => update({ [key]: e.target.value === 'true' })}
    >
      <option value="true">Да</option>
      <option value="false">Нет</option>
    </select>
  )

  const selectField = (
    key: string,
    placeholder: string,
    items: { id: number; label: string }[],
    allowNull = false,
  ) => {
    const current = (form[key] as number | undefined) ?? (allowNull ? null : 0)
    return (
      <select
        value={current ? String(current) : ''}
        onChange={(e) =>
          update({
            [key]:
              e.target.value === '' ? (allowNull ? null : 0) : Number(e.target.value),
          })
        }
      >
        <option value="">{placeholder}</option>
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {item.label}
          </option>
        ))}
      </select>
    )
  }

  const unitOptions = options.units.map((u) => ({ id: u.id, label: `${u.code} — ${u.name}` }))
  const contractorOptions = options.contractors.map((c) => ({ id: c.id, label: `${c.code} — ${c.name}` }))
  const objectOptions = options.objects.map((o) => ({ id: o.id, label: `${o.code} — ${o.name}` }))
  const stageOptions = options.stages.map((s) => ({ id: s.id, label: `${s.code} — ${s.name}` }))
  const workTypeOptions = options.workTypes.map((wt) => ({
    id: wt.id,
    label: `${wt.code} — ${wt.name}`,
  }))
  const workMethodOptions = options.workMethods.map((wm) => ({
    id: wm.id,
    label: `${wm.code} — ${wm.name}`,
  }))
  const userOptions = options.users.map((u) => ({
    id: u.id,
    label: `${u.full_name} (${u.max_user_id})`,
  }))

  switch (tab) {
    case 'objects':
      return (
        <>
          <td>{textField('code', 'Код')}</td>
          <td>{textField('name', 'Название')}</td>
          <td>
            <select
              value={String((form as unknown as AdminObject).execution_method || 'own')}
              onChange={(e) =>
                update({ execution_method: e.target.value as 'own' | 'contractor' })
              }
            >
              <option value="own">Собственные</option>
              <option value="contractor">Подрядчик</option>
            </select>
          </td>
          <td>{selectField('default_contractor_id', 'Подрядчик...', contractorOptions, true)}</td>
          <td>{textField('short_title', 'Короткий титул')}</td>
          <td>{textField('full_title', 'Полный титул')}</td>
          <td>{boolField('active')}</td>
          <td>{textField('sort_order', 'Порядок', 'number')}</td>
        </>
      )
    case 'units':
      return (
        <>
          <td>{textField('code', 'Код')}</td>
          <td>{textField('name', 'Название')}</td>
          <td>{textField('symbol', 'Обозначение')}</td>
          <td>{boolField('active')}</td>
          <td>{textField('sort_order', 'Порядок', 'number')}</td>
        </>
      )
    case 'equipment':
    case 'work-types':
      return (
        <>
          <td>{textField('code', 'Код')}</td>
          <td>{textField('name', 'Название')}</td>
          <td>{selectField('default_unit_id', 'Единица...', unitOptions, true)}</td>
          <td>{boolField('active')}</td>
          <td>{textField('sort_order', 'Порядок', 'number')}</td>
        </>
      )
    case 'object-stages': {
      return (
        <>
          <td>{selectField('object_id', 'Объект...', objectOptions)}</td>
          <td>{selectField('stage_id', 'Этап...', stageOptions)}</td>
          <td>{boolField('active')}</td>
        </>
      )
    }
    case 'work-type-methods':
      return (
        <>
          <td>{selectField('work_type_id', 'Вид работы...', workTypeOptions)}</td>
          <td>{selectField('work_method_id', 'Способ...', workMethodOptions)}</td>
          <td>{boolField('active')}</td>
        </>
      )
    case 'assignments':
      return (
        <>
          <td>{selectField('user_id', 'Пользователь...', userOptions)}</td>
          <td>{selectField('object_id', 'Объект...', objectOptions)}</td>
          <td>{textField('active_from', 'YYYY-MM-DD', 'date')}</td>
          <td>{textField('active_to', 'YYYY-MM-DD', 'date')}</td>
          <td>
            <select
              value={String((form as unknown as AdminAssignment).schedule_type || 'daily')}
              onChange={(e) =>
                update({ schedule_type: e.target.value as 'daily' | 'weekdays' })
              }
            >
              <option value="daily">Ежедневно</option>
              <option value="weekdays">Будни</option>
            </select>
          </td>
          <td>{boolField('active')}</td>
        </>
      )
    case 'users':
      return (
        <>
          <td>{textField('max_user_id', 'MAX ID')}</td>
          <td>{textField('full_name', 'ФИО')}</td>
          <td>
            <select
              value={String((form as unknown as AdminUser).role || 'responsible')}
              onChange={(e) =>
                update({ role: e.target.value as 'responsible' | 'manager' | 'admin' })
              }
            >
              <option value="responsible">Ответственный</option>
              <option value="manager">Менеджер</option>
              <option value="admin">Админ</option>
            </select>
          </td>
          <td>{boolField('active')}</td>
        </>
      )
    default:
      return (
        <>
          <td>{textField('code', 'Код')}</td>
          <td>{textField('name', 'Название')}</td>
          <td>{boolField('active')}</td>
          <td>{textField('sort_order', 'Порядок', 'number')}</td>
        </>
      )
  }
}
