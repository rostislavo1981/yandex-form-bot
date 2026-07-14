# 06. Frontend Mini App

Стек: React, Vite, TypeScript strict, обычный CSS. Mobile-first, ширина контента до 640 px.

## Экраны

- `/report` — ежедневный отчёт.
- `/reports` — список доступных отчётов.
- `/timesheet` — табель по объекту и периоду.
- `/status` — статус сдачи (manager/admin).
- `/admin/catalogs` — управление справочниками (manager/admin): табы, inline CRUD, Excel import/export.
- `/catalog-import` — прямой upload/preview/apply Excel (admin; резерв).

## Форма

1. Дата — сегодня.
2. Ответственный — текущий пользователь; выбор другого только manager/admin.
3. `SearchSelect` объекта: серверный поиск, последние/назначенные объекты сверху.
4. `SearchSelect` этапа: очищается при смене объекта, данные только для выбранного объекта.
5. Подрядчик появляется для contractor-объекта.
6. `EquipmentRows`: тип, принадлежность, единица, количество, удалить, добавить.
7. Персонал: ИТР, штатные, внештатные.
8. `WorkRows`: вид, допустимый способ, единица, количество, удалить, добавить.
9. Грунт и комментарий.
10. Проверка, отправка, экран успеха.

## SearchSelect

- debounce 250–350 ms;
- запрос начинается с 2 символов, но показывает последние/популярные без ввода;
- максимум 20 результатов;
- клавиатура и touch;
- loading, empty, error;
- отображает короткий `code` и полное `name`;
- не позволяет сохранить произвольный текст вместо ID.

## Табель

Сначала объект, затем период. На мобильном — горизонтальный scroll с закреплёнными первыми двумя колонками. Группы: персонал, техника, работы, грунт. Итоги справа; Excel скачивается через `window.WebApp.downloadFile` по HTTPS или обычный browser download fallback.

## Авторизация

Подключить MAX Bridge и читать только `window.WebApp.initData`. В dev frontend отправляет специальный dev header только когда backend запущен с `APP_ENV=dev`; production fallback запрещён.

## Состояния

У каждого экрана обязательны: loading, empty, validation error, network error, success. Двойное нажатие submit блокируется; каждый submit имеет новый UUID `Idempotency-Key`.

## Не делать в MVP

Redux, UI framework, offline sync, сложную админку, графики, редактирование отправленного отчёта.
