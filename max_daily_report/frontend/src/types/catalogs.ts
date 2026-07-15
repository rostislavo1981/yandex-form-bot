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

export interface ContractRef {
  id: number
  code: string
  full_name: string
  primary: boolean
}

export interface ObjectItem extends CatalogItem {
  contracts: ContractRef[]
}

export interface ObjectListResponse {
  items: ObjectItem[]
  total: number
}
