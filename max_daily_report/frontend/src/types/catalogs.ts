export interface CatalogItem {
  id: number
  code: string
  name: string
}

export interface CatalogItemWithSymbol extends CatalogItem {
  symbol: string
}

export interface CatalogListResponse {
  items: CatalogItem[]
  total: number
}
