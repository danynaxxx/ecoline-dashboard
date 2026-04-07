# Контекст проекта Ecoline — как мы считаем трафик и данные

> Последнее обновление: апрель 2026. Этот файл — источник правды для всех чатов и агентов работающих над проектом.

## Бизнес
Ecoline — замена окон в Канаде. Работают по всей стране, но в ограниченном списке городов (см. ниже). Средний чек варьируется по регионам. Основной KPI = **booked appointments** при целевом CPA.

## Структура трафика

**Два типа Meta-кампаний:**
- **Lead Gen (LG)** — instant forms внутри Meta. Высокий объём, дешевле CPL, качество лидов варьируется.
- **Conversion (CONV)** — трафик на лендинг. Дороже, но лид более "тёплый".

**Два типа географического таргетинга:**
- **National (ALL REGIONS)** — одна кампания на всю Канаду. Meta сама решает куда лить → контроль над регионами теряется.
- **Regional/City** — отдельные кампании на конкретные провинции/города. Объём меньше, контроль выше.

**Рекламные аккаунты:** ACC3, ACC4, ACC7, ACC8 (Ecoline Windows #3/#4/#7/#8).

## KPI-стек (снизу вверх)
```
Spend → Leads (CPL) → Appointments (CPA) → Sales (CPS) → Revenue (ROAS)
```
Сейчас мы меряем до Appointments надёжно. Revenue и ROAS в дашборде пока НЕ считаются — это основной пробел.

## Источники данных

**BigQuery (проект `ecolinew`):**
- `raw.leads` — web form submissions с UTM (source/medium/campaign), phone, email, postal_code, dt
- `raw.leads_status` — CRM статусы: `cf_booked_date`, `cf_appt_date`, `cf_sold_date`, `cf_cancelled_date`, amount, duplication flag
- `raw.calls` / `raw.calls_status` — inbound calls (DNI), фильтр first_call=TRUE
- `raw.city_map` — FSA (первые 3 символа postal) → city
- `raw.province_map` — первая буква postal → province
- `raw.spend_snap` / `raw.spend_geo_snap` — расходы Meta через Windsor AI (есть задержка)
- `report.*` pre-aggregated таблицы — имеют `amount` (revenue), `budget`, `sold`, `native_spend` (канал который мы не трекаем!)
- `raw.upd` / `raw.upd_hd` / `raw.updcalls` — CRM дампы с `ContactID` для cross-source матчинга (пока НЕ используем)

**Meta Ads API** (через MCP) — прямая интеграция без задержки Windsor. Данные кэшируются в JSON-файлы в `meta_cache/`.

**`meta_spend_cache.json`** — отдельный кэш ежедневного агрегированного спенда по всем 9 канадским Meta-аккаунтам. Обновляется автоматически по расписанию (ежедневно + глубокий пересинк каждый понедельник за последние 30 дней для корректировки Windsor-задержек). Структура: `{date, spend, clicks}` — сумма по всем аккаунтам за день.

## Как meta_spend_cache.json используется в дашборде

Файл читается через функцию `load_spend_daily()` в `utils/data.py`. Логика:

1. Сначала загружается кэш — для дат, которые в нём есть, данные берутся из файла (без задержки Windsor).
2. Для дат **не** покрытых кэшем — фолбэк на BigQuery (`raw.spend_snap`).

**Где кэш применяется (через `load_spend_daily`):**
- Trend-графики расходов по дням
- Сравнение периодов (comp_spend)
- Метрика "Meta Direct (API)" на панели сверки Windsor
- Total Meta Spend (period) в разделе Creative

**Где кэш НЕ применяется:**
- `load_spend()` — гео-разбивка по провинциям/городам идёт напрямую из BigQuery (`raw.spend_geo_snap`). Там всегда Windsor с задержкой.

Итого: **дневные тренды и суммарный спенд = кэш (актуально), разбивка по гео = BigQuery (с задержкой ~1-2 дня)**.

## Методология подсчёта лидов

Три уровня:
1. **Meta raw** — сырые лиды из Meta API, включают спам и дубли
2. **BQ all** — после SQL-фильтра (валидный phone/email или есть апп)
3. **BQ clean** — после дедупликации в окне 45 дней через функцию `apply_dedup()`

Пример за неделю 23–29 марта:
- Meta raw: 1,344
- BQ all: 1,306 (−38 на валидации)
- BQ clean: 1,240 (−66 на дедупе)

**CPL (raw)** = spend / Meta raw — заниженный, так как знаменатель завышен спамом
**CPL (clean)** = spend / BQ clean — настоящий CPL, совпадает с Overview

## Аппойнтменты

Считаются по `cf_booked_date` (дата бронирования), не по дате встречи. Это правильный момент конверсии.

В дашборде все метрики воронки keyed off **lead submission date**, не event date — т.е. "лиды этой недели и их аппойнтменты (в любое будущее время)".

**Важно:** dedup window 45 дней выбран произвольно. Нужно A/B тестить 30/45/60/90 против `raw.leads_status.duplication` (родной CRM флаг).

## Классификация кампаний

Парсим `utm_campaign`:
- **scope**: city / province / sub_regional / national / usa / other
- **camp_type**: LG / CONV / TRAFFIC / OTHER

National campaigns (ALL REGIONS) разбиваются на провинции через Meta API region breakdown, внутри провинции — по городам через BQ данные той же недели и того же camp_type.

## Активные города (верифицировано по 90-дневным BQ данным, апрель 2026)

| Провинция | Города |
|---|---|
| Alberta | Calgary, Edmonton, Red Deer, Lethbridge, Medicine Hat, Grande Prairie, Lloydminster |
| British Columbia | Vancouver, Victoria, Kelowna, Kamloops, Nanaimo, Prince George |
| Ontario | Ottawa, Kingston, ON |
| Manitoba | Winnipeg, Brandon, MB |
| Saskatchewan | Saskatoon, Regina, Moose Jaw |
| New Brunswick | Moncton, Fredericton, Saint John |
| Nova Scotia | Halifax, Sydney |
| Newfoundland | St. John's (в BQ: "St. Jhon's, NF" — тайпо, T13) |
| PEI | Charlottetown |

**НЕ активные Ontario города** (0 аппов): Toronto, Hamilton, London, Brampton, Mississauga

**"Bad geo" города** (лиды приходят из-за кривого FB таргетинга, аппов 0) — мониторим:
- Toronto (465 лидов/квартал), Thunder Bay (83), Kenora (39), NU/NT (27), Yukon (22), Sudbury (12)

## Маппинг города
1. Берём первые 3 символа postal_code → FSA (e.g. `T2P` = downtown Calgary)
2. JOIN с `raw.city_map` → город
3. Первая буква FSA + JOIN с `raw.province_map` → провинция
4. Если postal нет или кривой → "Unknown city" (обычно 0 аппов, не критично)

**Баги в city_map (pending fix):**
- T13: Тайпо "St. Jhon's, NF" вместо "St. John's" — костыль в коде, нужен UPDATE в BQ
- T14: Дубль Kingston: есть "Kingston" (0 аппов) и "Kingston, ON" (13 аппов) — разные FSA

## Источник лида (из UTM)

| utm_source | Dashboard source |
|---|---|
| facebook, meta, fb | META |
| google, adwords | GOOGLE |
| empty / null | DIRECT |
| всё остальное | OTHER |

Звонки атрибутируются к родительскому источнику (META, Affiliate). Calls = отдельная категория в некоторых срезах.

## Что уже построено в дашборде (Streamlit)

1. **Overview** — воронка Meta spend → leads → appts → sold, CPL/CPA/ROAS (ROAS пока фейковый, без revenue)
2. **Trends** — funnel по неделям/месяцам + **4-week appointment calendar** с YoY дельтой (−52 недели) и разбивкой Meta·LG / Meta·CONV / Calls / Affiliate
3. **Geography** — города/провинции, lead/appt/sold распределение
4. **Lead Detail** — raw таблица лидов
5. **Funnel Analysis** — детальная воронка с кастомными окнами
6. **Campaign Intelligence** — campaign-level метрики
7. **Source Comparison** — каналы рядом
8. **Meta Live** — прямая интеграция с Meta API через MCP. Province→city breakdown для national campaigns. Показывает Meta raw leads, BQ clean leads, CPL (raw), CPL (clean), CPM, CPC, CTR
9. **Prediction (ML v3)** — логистическая регрессия, 11,927 аппов 2024-2026. AUC 0.596, MAE 4.2 sales
10. **To Do & Feedback** — бэклог задач + форма фидбэка

## Ключевые решения из методологии
- Meta Live привязан к своему периоду, не к глобальному sidebar
- `combined_ml` фильтруется по Meta Live периоду чтобы цифры BQ совпадали
- Чистые лиды: email-only без CRM активности → НЕ clean
- Show Rate = showed_up / appts (было неправильно раньше)
- Upcoming: `>=today`; Pending = дата встречи прошла, CRM не обновлён

## Что НЕ считаем (основные пробелы)

1. **Revenue / ROAS** — `report.amount` не подключён. Главный пробел. Сейчас решения принимаются по CPL, должны по ROAS.
2. **Speed-to-contact** — `raw.calls` не используется для sales ops метрик (time-to-first-call, <5min %)
3. **Creative-level в Meta** — смотрим только campaign, не ad/creative. Нет frequency alerts, CTR decay мониторинга
4. **Sales team performance** — close rate by owner/city не считается
5. **Cohort-анализ** — сравниваем "last_7d spend vs last_7d appts", хотя sales созревают 30-90 дней
6. **LTV / repeat rate** — ContactID матчинг через upd_hd не используется
7. **Budget pacing** — `report.total.budget` не сравнивается со spend MTD
8. **Demographic/placement breakdown** в Meta — не трекаем, 18-34 сегмент может сливать 15-25% бюджета
9. **Native ads канал** — `report.daily.native_spend` есть, в дашборде нет

## Приоритеты (To Do)
- **P0**: Revenue в дашборд (Sprint 1), Speed-to-contact (Sprint 2), Creative-level Meta (Sprint 3)
- **P1**: Budget pacing, Cohort-анализ, Native ads, Media buyer expandable reports, Auto-refresh cache, Attribution window tuning
- **P2**: ContactID unification + LTV, Demographic breakdown, Province breakdown для всех периодов

## Правила работы над дашбордом
1. Любая новая фича / логика подсчёта / маппинг → обязательно обновляется страница "How It Works" (ru + en)
2. Задача реализована → убирается из To Do
3. Идея → попадает в To Do как новый тикет
4. Для подтверждения данных — прямые запросы в BigQuery, для live Meta — MCP инструменты

## Технический стек
- Streamlit + Plotly
- BigQuery через `google-cloud-bigquery`
- Pandas для трансформаций
- Numpy-only ML (логистическая регрессия вручную)
- Meta Ads API через Claude MCP tools + JSON cache в `meta_cache/`
- JSON persistence для To Do и feedback (`todo_data/`)

## Meta-анализ (этот чат, апрель 2026)

Выполнен анализ 24 месяцев (апр 2024 – апр 2026) по всем 11 Meta аккаунтам:

**Ключевые находки:**
- ACC7 — самый эффективный аккаунт: DCO формат даёт CPL $20–57
- Бюджетный sweet spot: $290–365K/месяц = ~4x ROAS; выше $400K ROAS падает до 2.5x
- LG кампании стабильно обходят CONV по CPL
- 2 US аккаунта (act_1406512109835943, act_5713736752045739) — данных нет, кампании не запускались
- В BQ нет spend данных за 2024 (raw.spend_snap только с Jan 2025) — пробел нужно закрыть

**Файл анализа:** `ecoline_meta_analysis.xlsx` (в этой папке) — 7 листов: Executive Summary, Account Summary, All Campaigns, Top Performers, Money Burners, Recommendations, Geo Performance.

**Следующий шаг по Meta-анализу:**
- Пересчитать анализ с правильными метриками: CPL (clean), CPA (cost per appointment), разбивка по городам и типу кампании (LG vs CONV)
- Подключить `raw.leads_status.cf_booked_date` для расчёта реального CPA по кампаниям
