# MAX Daily Report — Frontend

Vite + React + TypeScript shell для MAX Mini App.

## Скрипты

- `npm run dev` — dev server на http://127.0.0.1:3000 (проксирует `/api` на backend).
- `npm run build` — production build в `dist/`.
- `npm test` — vitest.

## Авторизация

Фронтенд читает `window.WebApp.initData` и отправляет в `X-Init-Data`. В dev-режиме fallback включён только если `VITE_ALLOW_DEV_AUTH=true`.
