import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ReportPage } from '../pages/ReportPage.tsx'
import type { CatalogItem, ObjectItem } from '../types/catalogs'

const { searchObjectsMock, searchStagesMock } = vi.hoisted(() => ({
  searchObjectsMock: vi.fn(),
  searchStagesMock: vi.fn(),
}))

const { submitReportMock } = vi.hoisted(() => ({ submitReportMock: vi.fn() }))

vi.mock('../api/catalogs', () => ({
  searchObjects: (...args: unknown[]) => searchObjectsMock(...args),
  searchStages: (...args: unknown[]) => searchStagesMock(...args),
  searchEquipment: () => Promise.resolve({ items: [], total: 0 }),
  searchWorkTypes: () => Promise.resolve({ items: [], total: 0 }),
  searchWorkMethods: () => Promise.resolve({ items: [], total: 0 }),
  listUnits: () => Promise.resolve({ items: [], total: 0 }),
}))

vi.mock('../api/reports', () => ({
  submitReport: (...args: unknown[]) => submitReportMock(...args),
}))

const stage: CatalogItem = { id: 100, code: 'STG-1', name: 'Этап 1' }

const objOneContract: ObjectItem = {
  id: 1,
  code: 'OBJ-1',
  name: 'Объект А',
  contracts: [
    { id: 10, code: 'C-10', full_name: 'Договор на строительство объекта А', primary: true },
  ],
}

const objNoContract: ObjectItem = {
  id: 2,
  code: 'OBJ-2',
  name: 'Объект Б',
  contracts: [],
}

const objTwoContracts: ObjectItem = {
  id: 3,
  code: 'OBJ-3',
  name: 'Объект В',
  contracts: [
    { id: 20, code: 'C-20', full_name: 'Договор один для объекта В', primary: true },
    { id: 21, code: 'C-21', full_name: 'Договор два для объекта В', primary: false },
  ],
}

const objLongName: ObjectItem = {
  id: 4,
  code: 'OBJ-LONG',
  name: 'ЖК Северная Долина',
  contracts: [
    {
      id: 30,
      code: 'C-30',
      full_name:
        'Очень длинное официальное полное название договора на выполнение строительно-монтажных работ с множеством реквизитов и дополнительных условий',
      primary: true,
    },
  ],
}

let lastPayload: Record<string, unknown> | null = null

async function selectObject(user: ReturnType<typeof userEvent.setup>, name: string) {
  const input = screen.getByLabelText('Объект')
  await user.click(input)
  await user.type(input, name)
  const option = await screen.findByText(name)
  await user.click(option)
}

async function selectStage(user: ReturnType<typeof userEvent.setup>, name: string) {
  const input = screen.getByLabelText('Этап')
  await user.click(input)
  await user.type(input, name)
  const option = await screen.findByText(name)
  await user.click(option)
}

describe('ReportPage object/contract selection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    submitReportMock.mockResolvedValue({ id: 1, status: 'created', late: false })
    searchStagesMock.mockResolvedValue({ items: [stage], total: 1 })
  })

  it('test_one_contract_auto_submitted', async () => {
    searchObjectsMock.mockResolvedValue({ items: [objOneContract], total: 1 })
    const user = userEvent.setup()
    render(<ReportPage />)

    await selectObject(user, 'Объект А')
    await selectStage(user, 'Этап 1')

    expect(screen.queryByLabelText('Договор / официальный объект')).not.toBeInTheDocument()

    await user.click(screen.getByText('Отправить'))

    await waitFor(() => expect(submitReportMock).toHaveBeenCalled())
    lastPayload = submitReportMock.mock.calls[0][0] as Record<string, unknown>
    expect(lastPayload.contract_id).toBe(10)
    expect(lastPayload.object_id).toBe(1)
  })

  it('test_two_contracts_show_select', async () => {
    searchObjectsMock.mockResolvedValue({ items: [objTwoContracts], total: 1 })
    const user = userEvent.setup()
    render(<ReportPage />)

    await selectObject(user, 'Объект В')

    const contractSelect = screen.getByLabelText('Договор / официальный объект')
    expect(contractSelect).toBeInTheDocument()

    await selectStage(user, 'Этап 1')

    await user.selectOptions(contractSelect, '21')

    await user.click(screen.getByText('Отправить'))

    await waitFor(() => expect(submitReportMock).toHaveBeenCalled())
    lastPayload = submitReportMock.mock.calls[0][0] as Record<string, unknown>
    expect(lastPayload.contract_id).toBe(21)
  })

  it('test_change_object_clears_stage_and_contract', async () => {
    searchObjectsMock.mockResolvedValue({ items: [objOneContract, objNoContract], total: 2 })
    const user = userEvent.setup()
    render(<ReportPage />)

    await selectObject(user, 'Объект А')
    await selectStage(user, 'Этап 1')

    expect(screen.getByLabelText('Этап')).toHaveValue('Этап 1 (STG-1)')

    const objectSelect = screen.getAllByTestId('search-select')[0]
    await user.click(within(objectSelect).getByLabelText('Очистить'))
    await selectObject(user, 'Объект Б')

    const stageSelect = screen.getAllByTestId('search-select')[1]
    expect(within(stageSelect).getByLabelText('Этап')).toHaveValue('')
    expect(screen.queryByLabelText('Договор / официальный объект')).not.toBeInTheDocument()
  })

  it('test_search_long_name_returns_short_object', async () => {
    searchObjectsMock.mockResolvedValue({ items: [objLongName], total: 1 })
    const user = userEvent.setup()
    render(<ReportPage />)

    const input = screen.getByLabelText('Объект')
    await user.type(input, 'ЖК')

    expect(await screen.findByText('ЖК Северная Долина')).toBeInTheDocument()
    expect(screen.getByText(/Очень длинное официальное полное название/)).toBeInTheDocument()
  })

  it('test_long_text_does_not_break_layout', async () => {
    searchObjectsMock.mockResolvedValue({ items: [objLongName], total: 1 })
    const user = userEvent.setup()
    render(<ReportPage />)

    const input = screen.getByLabelText('Объект')
    await user.type(input, 'ЖК')

    const subtitle = await screen.findByText(/Очень длинное официальное полное название/)
    expect(subtitle.className).toContain('search-select-option-subtitle')
    expect(subtitle.classList.contains('search-select-option-subtitle')).toBe(true)
  })
})
