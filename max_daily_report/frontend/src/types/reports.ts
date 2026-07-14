export interface ReportFormData {
  report_date: string
  object_id: number | null
  stage_id: number | null
  contractor_id: number | null
  staff_itr: number
  staff_internal: number
  staff_external: number
  soil_export_m3: string
  comment: string
}
