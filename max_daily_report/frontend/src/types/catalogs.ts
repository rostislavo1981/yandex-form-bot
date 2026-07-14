export interface CatalogItem {
  id: number
  code: string
  name: string
}

export interface CatalogListResponse {
  items: CatalogItem[]
  total: number
}
