# Roadmap

> Исторический roadmap V1. Единственный актуальный backlog нового MVP: [`max-mini-app-spec/08_implementation_plan.md`](max-mini-app-spec/08_implementation_plan.md).

## v0.1.0 (current — MVP+1) ✅
- [x] YandexGPT-парсер (12 полей формы)
- [x] Playwright-заполнение Яндекс.Формы
- [x] Яндекс.Диск (JSON + PNG)
- [x] SQLite submissions
- [x] Excel-сводная
- [x] MAX-бот (long polling)
- [x] FastAPI + Mini App + HMAC
- [x] 152 теста

## v0.2.0 — production-ready

### Высокий приоритет
- [ ] **Реальные CSS-селекторы** (опубликованная форма)
- [ ] **142 поля формы** (вместо 12 placeholder-ов)
- [ ] **Webhook вместо long polling** (быстрее, надёжнее)
- [ ] **HTTPS + reverse-proxy** (Cloudflare / Caddy)
- [ ] **Multi-prorab** (убрать `DEFAULT_FOREMAN=Степанов`)
- [ ] **Production secrets** (Vault / K8s secrets)

### Средний
- [x] **Inline-редактирование** справочников в Mini App (`/admin/catalogs`) — done in I22
- [ ] **Дашборд**: графики работ/людей/грунта по дням (Chart.js)
- [ ] **Уведомления** прорабам в 20:00 (cron → MAX)
- [ ] **Фильтр по объекту** (сейчас только foreman)
- [ ] **Пагинация** /api/summary (для больших периодов)

### Низкий
- [ ] **Экспорт в PDF** (через weasyprint)
- [ ] **Telegram-мост** (MAX API → TG forwarding)
- [ ] **WebSocket live-updates** (вместо перезагрузки)
- [ ] **Multi-tenant** (несколько организаций)

## v0.3.0 — advanced

- [ ] **OCR** для сканов от руки (Tesseract / Yandex Vision)
- [ ] **LLM-нормализация** (разные форматы дат, ед. измерения)
- [ ] **Anomaly detection** (стало меньше людей, чем вчера — алерт)
- [ ] **Отчёты начальству** (еженедельный PDF на email)
- [ ] **PWA** (Offline-режим для Mini App)

## v1.0.0 — стабильность

- [ ] SLO 99.5%
- [ ] P95 latency < 30s (отчёт → форма)
- [ ] Full observability (Prometheus + Grafana)
- [ ] Disaster recovery (бэкап SQLite → Диск)
- [ ] CI/CD (auto-deploy на merge)
- [ ] Load testing (100 отчётов/мин)

---

## Открытые вопросы (нужна обратная связь от пользователя)

| Вопрос | Где | Без этого |
|---|---|---|
| Точные CSS-селекторы формы | `backend/forms/fields.py` | MVP не заполнит форму в проде |
| OAuth-refresh токен | `YANDEX_DISK_REFRESH_TOKEN` | Через 30 дней Диск отвалится |
| Какие именно 142 поля? | `backend/forms/fields.py` | Не знаю, что парсить |
| Домен для HTTPS | `WEBAPP_PUBLIC_URL` | Mini App не откроется |
| Multi-prorab нужен? | `Settings.default_foreman` | Пока один прораб |
| Cron напоминания в 20:00? | `backend/cli/run_reminder.py` | Прорабы забывают |

## Идеи вне scope (когда-нибудь)

- Интеграция с 1С (выгрузка в бухгалтерию)
- Мобильное приложение (Flutter)
- Голосовой ввод отчёта (Whisper)
- AR-фото объекта (отчёт с фото)
- Система задач (что прораб должен сделать завтра)
