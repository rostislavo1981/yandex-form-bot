import { api } from './client'
import type { CatalogListResponse } from '../types/catalogs'

export interface ReportCreatedResponse {
  id: number
  status: string
  late: boolean
}

export async function submitReport(
  payload: unknown,
  idempotencyKey: string,
): Promise<ReportCreatedResponse> {
  return api.post<ReportCreatedResponse>('/api/reports', payload, idempotencyKey)
}

export async function listReports(limit = 20): Promise<CatalogListResponse> {
  return api.get<CatalogListResponse>(`/api/reports?limit=${limit}`)
}
