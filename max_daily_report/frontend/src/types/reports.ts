export interface StaffValues {
  itr: number
  internal: number
  external: number
}

export interface EquipmentRow {
  id: string
  equipment_type_id: number | null
  ownership: 'own' | 'rented' | 'contractor'
  unit_id: number | null
  quantity: string
  comment: string
}

export interface ReportFormData {
  report_date: string
  object_id: number | null
  stage_id: number | null
  contractor_id: number | null
  staff: StaffValues
  soil_export_m3: string
  equipment: EquipmentRow[]
  works: []
  comment: string
}
