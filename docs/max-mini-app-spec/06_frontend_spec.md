# 06. Frontend — спецификация

Стек: **React 18 + Vite + TypeScript**. Стилизация — обычный CSS (без UI-либ в MVP). Состояние — `useState`/`useReducer`, без Redux.

## Роутинг

Два экрана:
- `/` — форма отчёта.
- `/summary` — сводная.

Используем `react-router-dom` (минимальный). Или самодельный `useState` для таба — тоже приемлемо в MVP.

## Инициализация

При старте приложения:
1. Взять `initData` из `window.MaxApp` (или dev-заглушку в `import.meta.env.DEV`).
2. Отправить `GET /api/bootstrap` c заголовком `X-Auth-InitData`.
3. Положить справочники в контекст `BootstrapContext`.
4. Если 401 — показать экран «Откройте приложение через MAX».

## Экран 1: форма отчёта (`/`)

### Секции (в порядке сверху вниз)

**1. Основные данные**
- Дата (`<input type="date">`, по умолчанию сегодня).
- Ответственный (`<select>`, по умолчанию — `current_user`).
- Объект (`<select>` со всеми `objects`).
- Этап (`<select>`, фильтруется по `stages.filter(s => s.object_id === selected.object_id)`).
- Подрядчик (`<select>` со всеми `contractors`) — **показывается только если** `selectedObject.execution_method === 'contractor'`.
- Комментарий (`<textarea>`).

**2. Техника** (динамические строки)
Кнопка «+ Добавить строку». Каждая строка:
- `equipment` (select) → при выборе автоматически подставляется `unit = equipment.default_unit_id`.
- `unit` (select, можно поменять).
- `quantity` (`<input type="number" step="0.01" min="0.01">`).
- `ownership` (radio: собственная / арендованная / подрядчика).
- Кнопка «×» — удалить строку.

**3. Персонал** — секция видна **только если** `selectedObject.execution_method === 'own'`.
- ИТР (`number`, min=0).
- Штатные рабочие (`number`, min=0).
- Внештатные рабочие (`number`, min=0).

**4. Работы** (динамические строки)
- `work_type` (select) → auto `unit`.
- `unit` (select).
- `quantity` (number).
- `method` (text, опц.).
- Кнопка «×».

**5. Вывоз грунта**
- `soil_export_m3` (number, min=0, default=0).

**6. Отправка**
- Кнопка «Отправить» (disabled пока форма невалидна).
- Индикатор загрузки при `POST /api/reports`.
- После успеха: зелёный баннер «✅ Отчёт №42 отправлен», через 2 сек — сброс формы или закрытие webview через `window.MaxApp?.close()`.

### Клиентская валидация

- Обязательные: date, object, stage, responsible.
- Если объект подрядный — обязателен contractor.
- Хотя бы одно из: техника, работа, `soil_export_m3 > 0`.
- Все `quantity > 0`.

Ошибки показываются под соответствующим полем красным текстом.

### Автосохранение (nice-to-have, не MVP)
`localStorage` черновик с ключом `draft:<date>`. При открытии формы — предложить восстановить.

## Экран 2: сводная (`/summary`)

**Верх страницы:**
- Быстрые чипы: `Сегодня` / `Вчера` / `7 дней` / `30 дней`.
- Два `<input type="date">` (from/to).
- Кнопка «Применить».
- Кнопка «📥 Excel».

**Карточки статистики:**
- Отчётов: N
- Всего людей: N
- Часов техники: N
- Грунт, м³: N

**Список отчётов:**
Каждая карточка:
```
📅 2026-07-13   БОГ-КЛ-04 · Разработка траншеи
👤 Казнадеев И.   🧑‍🔧 6 чел   🚜 8 ч   ♻️ 24.5 м³
```
Тап по карточке → раскрыть детали (строки техники/работ).

## Общие компоненты

- `ApiClient` (тонкая обёртка над `fetch` с `X-Auth-InitData`).
- `BootstrapContext` (Provider, кэш справочников).
- `useReport` (хук управления формой).
- `Banner` (успех/ошибка).

## Структура frontend

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── src/
    ├── main.tsx              # entry
    ├── App.tsx               # роутинг
    ├── api.ts                # ApiClient + типы
    ├── auth.ts               # initData helper
    ├── contexts/
    │   └── BootstrapContext.tsx
    ├── pages/
    │   ├── ReportForm.tsx
    │   └── Summary.tsx
    ├── components/
    │   ├── EquipmentRow.tsx
    │   ├── WorkRow.tsx
    │   ├── StaffBlock.tsx
    │   ├── SummaryCard.tsx
    │   └── Banner.tsx
    ├── hooks/
    │   └── useReport.ts
    └── styles/
        └── main.css
```

## Стили

- Мобильный first: `max-width: 600px`, всё под палец.
- Тёмная тема — не обязательна в MVP.
- CSS-переменные для цветов (единый акцент = синий #2E7BE9).

## Типы API (TypeScript)

Файл `src/api.ts`:
```ts
export interface BootstrapResponse {
  current_user: User;
  users: User[];
  objects: ObjectSite[];
  stages: Stage[];
  contractors: Contractor[];
  units: Unit[];
  equipment: Equipment[];
  work_types: WorkType[];
}

export interface User { id: number; full_name: string; role: string; }
export interface ObjectSite {
  id: number;
  title_code: string;
  name: string;
  execution_method: "own" | "contractor";
  default_contractor_id: number | null;
}
// ...
```

Держим типы в одном файле, чтобы не разъезжались с backend'ом. В идеале — генерить из OpenAPI (`fastapi` его отдаёт), но в MVP руками.
