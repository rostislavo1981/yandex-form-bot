import { api } from './client'
import type { CatalogItemWithSymbol, CatalogListResponse } from '../types/catalogs'

export async function searchObjects(q: string, limit = 20): Promise<CatalogListResponse> {
  const encoded = encodeURIComponent(q)
  return api.get<CatalogListResponse>(`/api/catalogs/objects?q=${encoded}&limit=${limit}`)
}

export async function searchStages(
  objectId: number,
  q: string,
  limit = 20,
): Promise<CatalogListResponse> {
  const encoded = encodeURIComponent(q)
  return api.get<CatalogListResponse>(
    `/api/catalogs/objects/${objectId}/stages?q=${encoded}&limit=${limit}`,
  )
}

export async function searchEquipment(q: string, limit = 20): Promise<CatalogListResponse> {
  const encoded = encodeURIComponent(q)
  return api.get<CatalogListResponse>(`/api/catalogs/equipment?q=${encoded}&limit=${limit}`)
}

export async function searchWorkTypes(q: string, limit = 20): Promise<CatalogListResponse> {
  const encoded = encodeURIComponent(q)
  return api.get<CatalogListResponse>(`/api/catalogs/work-types?q=${encoded}&limit=${limit}`)
}

export async function searchWorkMethods(
  workTypeId: number,
  q: string,
  limit = 20,
): Promise<CatalogListResponse> {
  const encoded = encodeURIComponent(q)
  return api.get<CatalogListResponse>(
    `/api/catalogs/work-types/${workTypeId}/methods?q=${encoded}&limit=${limit}`,
  )
}

export async function listUnits(limit = 50): Promise<{ items: CatalogItemWithSymbol[]; total: number }> {
  return api.get<{ items: CatalogItemWithSymbol[]; total: number }>(`/api/catalogs/units?limit=${limit}`)
}
