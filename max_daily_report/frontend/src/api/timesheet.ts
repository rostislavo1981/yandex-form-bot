import { api } from './client'

export interface TimesheetRow {
  category: string
  item_name: string
  ownership_or_method: string
  unit: string
  values: string[]
  total: string
  average: string
  max: string
}

export interface TimesheetResponse {
  object_id: number
  object_code: string
  object_name: string
  date_from: string
  date_to: string
  days: string[]
  rows: TimesheetRow[]
  missing_days: string[]
}

export async function fetchTimesheet(
  objectId: number,
  dateFrom: string,
  dateTo: string,
): Promise<TimesheetResponse> {
  return api.get<TimesheetResponse>(
    `/api/timesheet/${objectId}?date_from=${dateFrom}&date_to=${dateTo}`,
  )
}
