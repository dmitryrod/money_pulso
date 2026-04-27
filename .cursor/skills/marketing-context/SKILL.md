---
name: marketing-context
description: >-
  Single source of truth for product positioning, ICP, differentiation, and brand voice.
  Read before any other marketing skill. Use when creating or updating marketing foundation docs.
---

# Marketing Context

Канонический контекст маркетинга для проекта. Другие marketing skills **читают полный текст первым** и не дублируют уже зафиксированные факты.

## Где хранить

- **Канон текста приложения:** [`app/docs/marketing/context.md`](../../../app/docs/marketing/context.md) (оглавление: [`app/docs/marketing/README.md`](../../../app/docs/marketing/README.md)).
- **Указатель в Cursor:** [`.cursor/marketing-context.md`](../../marketing-context.md) — не дублирует секции; ведёт на `app/docs/marketing/`.
- **Шаблон пустых секций:** [`.cursor/marketing-context.example.md`](../../marketing-context.example.md) — для черновика перед переносом в `app/docs/marketing/context.md`.
- Legacy upstream: `.agents/product-marketing-context.md` — если есть только он, предложи миграцию в `app/docs/marketing/context.md`.
- **Исследования / GTM / roadmap / synthesis:** каталог [`app/docs/marketing/research/`](../../../app/docs/marketing/research/) — см. [`marketing-research-playbook`](../marketing-research-playbook/SKILL.md).
- **Тактические артефакты** (копирайт, email, варианты CTA): по умолчанию [`app/docs/marketing/artifacts/`](../../../app/docs/marketing/artifacts/) — см. агент `marketing`.

## Когда использовать

- Перед копирайтом, CRO, SEO, launch, pricing, исследованием клиентов
- Когда меняется продукт, ICP, цены или позиционирование

## Workflow

1. Проверь существование **`app/docs/marketing/context.md`** (и при необходимости указателя `.cursor/marketing-context.md`).
2. Если канона нет — предложи: авто-черновик из репо (`app/docs/README.md`, `ARCHITECTURE.md`, `app/`) или пошаговый Q&A; заполняй в `app/docs/marketing/context.md`.
3. Обновляй только затронутые секции; фиксируй дату в шапке `context.md`.

## Структура документа (обязательные секции)

```markdown
# Marketing Context
*Last updated: YYYY-MM-DD*

## Product Overview
**One-liner:**
**What it does:**
**Category / shelf:**
**Type:** (SaaS, service, marketplace, …)
**Business model:**

## Target Audience
**ICP:** (firmographics, technographics)
**Decision-makers / personas:** (кратко)
**Jobs to be done:**
**Primary use cases:**

## Problems & Pain
**Core problem:**
**Cost of status quo:**
**Why alternatives fail:**

## Competitive Landscape
**Direct / secondary / indirect** — по одному предложению каждый + чем сильнее/слабее

## Differentiation
**Claims:** (проверяемые)
**Proof:** (логотипы, метрики, кейсы)

## Objections & Anti-personas
| Objection | Response |
|-----------|----------|
**Not for:** (anti-ICP)

## Customer Language
**Verbatim quotes:** (реальные фразы с интервью/тикетов/отзывов)
**Words to use / avoid:**

## Brand Voice
**Tone:** **Style:** **Personality:**

## Goals & KPIs
**North star:** **Primary conversion:** **Известные метрики:**

## Constraints
**Compliance / brand / budget / geography / no-go channels:**
```

## Связь с upstream

Источник паттернов: [product-marketing-context на skills.sh](https://skills.sh/coreyhaines31/marketingskills/product-marketing-context) — структура совместима; **текст канона** в этом репо — `app/docs/marketing/context.md`.

## Связанные skills

- [`marketing-router`](../marketing-router/SKILL.md) — выбор leaf-skill по intent
- [`marketing-research-playbook`](../marketing-research-playbook/SKILL.md) — полный research/GTM цикл
