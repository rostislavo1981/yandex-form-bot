from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CatalogItem(BaseModel):
    id: int
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class CatalogItemWithSymbol(BaseModel):
    id: int
    code: str
    name: str
    symbol: str

    model_config = ConfigDict(from_attributes=True)


class CatalogListResponse(BaseModel):
    items: list[CatalogItem]
    total: int


class UnitListResponse(BaseModel):
    items: list[CatalogItemWithSymbol]
    total: int


class ContractRef(BaseModel):
    id: int
    code: str
    full_name: str
    primary: bool

    model_config = ConfigDict(from_attributes=True)


class ObjectItem(BaseModel):
    id: int
    code: str
    name: str
    contracts: list[ContractRef] = []

    model_config = ConfigDict(from_attributes=True)


class ObjectListResponse(BaseModel):
    items: list[ObjectItem]
    total: int
