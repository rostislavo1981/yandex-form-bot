import { api } from './client'
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
} from '../types/admin'

const base = '/api/admin/catalogs'

function getInitData(): string {
  if (typeof window === 'undefined') {
    return ''
  }
  const webApp = window.WebApp
  if (webApp?.initData) {
    return webApp.initData
  }
  if (import.meta.env.VITE_ALLOW_DEV_AUTH === 'true') {
    return 'dev'
  }
  return ''
}

export async function listObjects(): Promise<AdminObject[]> {
  return api.get<AdminObject[]>(`${base}/objects`)
}

export async function createObject(data: Omit<AdminObject, 'id'>): Promise<AdminObject> {
  return api.post<AdminObject>(`${base}/objects`, data)
}

export async function updateObject(id: number, data: Omit<AdminObject, 'id'>): Promise<AdminObject> {
  return api.put<AdminObject>(`${base}/objects/${id}`, data)
}

export async function deleteObject(id: number): Promise<void> {
  return api.delete(`${base}/objects/${id}`)
}

export async function listStages(): Promise<AdminCatalogItem[]> {
  return api.get<AdminCatalogItem[]>(`${base}/stages`)
}

export async function createStage(data: Omit<AdminCatalogItem, 'id'>): Promise<AdminCatalogItem> {
  return api.post<AdminCatalogItem>(`${base}/stages`, data)
}

export async function updateStage(id: number, data: Omit<AdminCatalogItem, 'id'>): Promise<AdminCatalogItem> {
  return api.put<AdminCatalogItem>(`${base}/stages/${id}`, data)
}

export async function deleteStage(id: number): Promise<void> {
  return api.delete(`${base}/stages/${id}`)
}

export async function listContractors(): Promise<AdminCatalogItem[]> {
  return api.get<AdminCatalogItem[]>(`${base}/contractors`)
}

export async function createContractor(data: Omit<AdminCatalogItem, 'id'>): Promise<AdminCatalogItem> {
  return api.post<AdminCatalogItem>(`${base}/contractors`, data)
}

export async function updateContractor(id: number, data: Omit<AdminCatalogItem, 'id'>): Promise<AdminCatalogItem> {
  return api.put<AdminCatalogItem>(`${base}/contractors/${id}`, data)
}

export async function deleteContractor(id: number): Promise<void> {
  return api.delete(`${base}/contractors/${id}`)
}

export async function listUnits(): Promise<AdminUnit[]> {
  return api.get<AdminUnit[]>(`${base}/units`)
}

export async function createUnit(data: Omit<AdminUnit, 'id'>): Promise<AdminUnit> {
  return api.post<AdminUnit>(`${base}/units`, data)
}

export async function updateUnit(id: number, data: Omit<AdminUnit, 'id'>): Promise<AdminUnit> {
  return api.put<AdminUnit>(`${base}/units/${id}`, data)
}

export async function deleteUnit(id: number): Promise<void> {
  return api.delete(`${base}/units/${id}`)
}

export async function listEquipment(): Promise<AdminEquipment[]> {
  return api.get<AdminEquipment[]>(`${base}/equipment`)
}

export async function createEquipment(data: Omit<AdminEquipment, 'id'>): Promise<AdminEquipment> {
  return api.post<AdminEquipment>(`${base}/equipment`, data)
}

export async function updateEquipment(id: number, data: Omit<AdminEquipment, 'id'>): Promise<AdminEquipment> {
  return api.put<AdminEquipment>(`${base}/equipment/${id}`, data)
}

export async function deleteEquipment(id: number): Promise<void> {
  return api.delete(`${base}/equipment/${id}`)
}

export async function listWorkTypes(): Promise<AdminWorkType[]> {
  return api.get<AdminWorkType[]>(`${base}/work-types`)
}

export async function createWorkType(data: Omit<AdminWorkType, 'id'>): Promise<AdminWorkType> {
  return api.post<AdminWorkType>(`${base}/work-types`, data)
}

export async function updateWorkType(id: number, data: Omit<AdminWorkType, 'id'>): Promise<AdminWorkType> {
  return api.put<AdminWorkType>(`${base}/work-types/${id}`, data)
}

export async function deleteWorkType(id: number): Promise<void> {
  return api.delete(`${base}/work-types/${id}`)
}

export async function listWorkMethods(): Promise<AdminCatalogItem[]> {
  return api.get<AdminCatalogItem[]>(`${base}/work-methods`)
}

export async function createWorkMethod(data: Omit<AdminCatalogItem, 'id'>): Promise<AdminCatalogItem> {
  return api.post<AdminCatalogItem>(`${base}/work-methods`, data)
}

export async function updateWorkMethod(id: number, data: Omit<AdminCatalogItem, 'id'>): Promise<AdminCatalogItem> {
  return api.put<AdminCatalogItem>(`${base}/work-methods/${id}`, data)
}

export async function deleteWorkMethod(id: number): Promise<void> {
  return api.delete(`${base}/work-methods/${id}`)
}

export async function listObjectStages(): Promise<AdminObjectStage[]> {
  return api.get<AdminObjectStage[]>(`${base}/object-stages`)
}

export async function createObjectStage(data: Omit<AdminObjectStage, 'id' | 'object_code' | 'stage_code'>): Promise<AdminObjectStage> {
  return api.post<AdminObjectStage>(`${base}/object-stages`, data)
}

export async function deleteObjectStage(id: number): Promise<void> {
  return api.delete(`${base}/object-stages/${id}`)
}

export async function listWorkTypeMethods(): Promise<AdminWorkTypeMethod[]> {
  return api.get<AdminWorkTypeMethod[]>(`${base}/work-type-methods`)
}

export async function createWorkTypeMethod(data: Omit<AdminWorkTypeMethod, 'id' | 'work_type_code' | 'work_method_code'>): Promise<AdminWorkTypeMethod> {
  return api.post<AdminWorkTypeMethod>(`${base}/work-type-methods`, data)
}

export async function deleteWorkTypeMethod(id: number): Promise<void> {
  return api.delete(`${base}/work-type-methods/${id}`)
}

export async function listAssignments(): Promise<AdminAssignment[]> {
  return api.get<AdminAssignment[]>(`${base}/assignments`)
}

export async function createAssignment(data: Omit<AdminAssignment, 'id' | 'user_name' | 'object_code'>): Promise<AdminAssignment> {
  return api.post<AdminAssignment>(`${base}/assignments`, data)
}

export async function deleteAssignment(id: number): Promise<void> {
  return api.delete(`${base}/assignments/${id}`)
}

export async function listAdminUsers(): Promise<AdminUser[]> {
  return api.get<AdminUser[]>(`${base}/users`)
}

export async function createUser(data: Omit<AdminUser, 'id'>): Promise<AdminUser> {
  return api.post<AdminUser>(`${base}/users`, data)
}

export async function updateUser(id: number, data: Omit<AdminUser, 'id'>): Promise<AdminUser> {
  return api.put<AdminUser>(`${base}/users/${id}`, data)
}

export async function deleteUser(id: number): Promise<void> {
  return api.delete(`${base}/users/${id}`)
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

function downloadBlob(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(url)
}

export async function exportCatalogs(): Promise<void> {
  const response = await fetch(`${API_BASE}/api/catalogs/export.xlsx`, {
    headers: { 'X-Init-Data': getInitData() },
  })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  const blob = await response.blob()
  downloadBlob(blob, 'catalogs.xlsx')
}

export async function downloadTemplate(): Promise<void> {
  const response = await fetch(`${API_BASE}/api/catalogs/template.xlsx`, {
    headers: { 'X-Init-Data': getInitData() },
  })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  const blob = await response.blob()
  downloadBlob(blob, 'template.xlsx')
}

export async function importCatalogs(file: File): Promise<unknown> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await fetch(`${API_BASE}/api/catalogs/import/apply`, {
    method: 'POST',
    headers: { 'X-Init-Data': getInitData() },
    body: formData,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail = body.error || body.detail
    throw new Error(
      typeof detail === 'string'
        ? detail
        : detail
          ? JSON.stringify(detail)
          : `HTTP ${response.status}`,
    )
  }
  return response.json()
}
