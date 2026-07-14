import { api } from './client'
import type { CatalogListResponse } from '../types/catalogs'

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
