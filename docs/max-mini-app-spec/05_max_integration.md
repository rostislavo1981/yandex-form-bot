# 05. Интеграция с MAX

Актуальность: официальная документация MAX, проверено 2026-07-14.

## Bot API

- Base URL: `https://platform-api2.max.ru`.
- Авторизация: `Authorization: <MAX_BOT_TOKEN>`.
- Отправка: `POST /messages`.
- Webhook: `POST /subscriptions`; production использует только webhook.
- Long polling `GET /updates` допускается для локальной диагностики.
- Inline-клавиатура передаётся как attachment `inline_keyboard`.
- Нужные типы кнопок: `open_app`, `callback`, `message`, `link`.
- Редактирование пульта: `PUT /messages`.
- Закрепление группового пульта: `PUT /chats/{chatId}/pin`; бот должен быть администратором с правом `pin_message`.

## Mini App Bridge

Frontend обязательно подключает:

```html
<script src="https://st.max.ru/js/max-web-app.js"></script>
```

Официальный глобальный объект — `window.WebApp`. Используются `initData`, `initDataUnsafe`, `ready()` и поддерживаемый Bridge метод закрытия, если он есть в установленной версии. `initDataUnsafe` разрешено использовать только для отображения, не для авторизации.

## Валидация initData

Использовать алгоритм из `https://dev.max.ru/docs/webapps/validation`:

1. Разобрать query string и потребовать ровно один `hash`.
2. Исключить `hash`, URL-decode значения, отсортировать по ключу.
3. Собрать `launch_params` как `key=value` через `\n`.
4. `secret_key = HMAC_SHA256(key="WebAppData", message=bot_token)`.
5. `expected = hex(HMAC_SHA256(key=secret_key, message=launch_params))`.
6. Сравнить `hmac.compare_digest`.
7. Проверить `auth_date`; TTL задаётся конфигом, default 1 час.
8. Декодировать `user` JSON и использовать `user.id` как MAX ID.

Формула `HMAC_SHA256(authDate + phone + userId, botToken)` относится к проверке номера телефона и **не является** общей валидацией `initData`.

## Групповой пульт

Закреплённое сообщение:

```text
[ 📝 Заполнить отчёт ]
[ 📊 Статус сегодня ] [ 📅 Табель ]
[ 📥 Excel ]          [ 👥 Кто не сдал ]
[ ℹ️ Помощь ]
```

`control_message_id` хранится в `max_groups`. При запуске и утром сервис проверяет пульт: обновляет существующий или создаёт и закрепляет новый.

## Личный пульт

```text
[ 📝 Заполнить отчёт ]
[ 📋 Мои отчёты ] [ 📅 Мой табель ]
[ 🏗 Мои объекты ] [ 📥 Excel ]
[ ↩️ Рабочая группа ]
```

MAX не предоставляет групповой pin endpoint для личного диалога, поэтому бот хранит `private_control_message_id`, редактирует пульт и повторно показывает его после завершённых действий. `/start` и `/menu` восстанавливают пульт.

## Уведомления

После отчёта: дата, объект, этап, ФИО, персонал, краткие итоги техники/работ/грунта и кнопки «Подробности», «Табель объекта», «Заполнить ещё».

Вечером: только `pending`, сгруппированные по ФИО и объекту, плюс кнопка заполнения.

Утром: expected/submitted/late/missed и список ФИО с объектами, плюс кнопки табеля и Excel.

## Безопасность webhook

Подписка создаётся с отдельным `WEBHOOK_SECRET`. Реализация обязана сверить фактический заголовок/поле секрета с текущей схемой официального endpoint перед кодированием. Raw updates можно логировать только с маскированием телефонов, токенов и initData.

## Проверка перед production

- Реальный update `bot_started`.
- Реальный `message_callback`.
- `open_app` из группы и личного диалога.
- Права бота на pin.
- Валидация реального `window.WebApp.initData`.
- Доставка webhook по HTTPS.
- Переход API на `platform-api2.max.ru` и актуальные требования сертификатов.
