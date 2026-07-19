export interface AdminCatalogItem {
  id: number
  code: string
  name: string
  active: boolean
  sort_order: number | null
}

export interface AdminObject extends AdminCatalogItem {
  short_title: string | null
  full_title: string | null
  execution_method: 'own' | 'contractor' | null
  default_contractor_id: number | null
}

export interface AdminUnit extends AdminCatalogItem {
  symbol: string
}

export interface AdminEquipment extends AdminCatalogItem {
  default_unit_id: number | null
}

export interface AdminWorkType extends AdminCatalogItem {
  default_unit_id: number | null
}

export interface AdminObjectStage {
  id: number
  object_id: number
  stage_id: number
  active: boolean
  object_code: string
  stage_code: string
}

export interface AdminWorkTypeMethod {
  id: number
  work_type_id: number
  work_method_id: number
  active: boolean
  work_type_code: string
  work_method_code: string
}

export interface AdminAssignment {
  id: number
  user_id: number
  object_id: number
  active_from: string
  active_to: string
  schedule_type: 'daily' | 'weekdays'
  active: boolean
  user_name: string
  object_code: string
}

export interface AdminUser {
  id: number
  max_user_id: string
  full_name: string
  role: 'responsible' | 'manager' | 'admin'
  active: boolean
}

export type CatalogTab =
  | 'objects'
  | 'stages'
  | 'contractors'
  | 'units'
  | 'equipment'
  | 'work-types'
  | 'work-methods'
  | 'object-stages'
  | 'work-type-methods'
  | 'assignments'
  | 'users'
