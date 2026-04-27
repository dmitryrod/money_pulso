---
name: product-naming
description: >-
  Product, brand, and domain naming: strategies, scored shortlists, validation.
  Use when naming or renaming a product/app/company, brainstorming domains, or aligning a name with positioning.
---

# Product naming (brand + domain)

Цель: дать **короткий список проверяемых имён** с обоснованием, скорингом и следующими шагами по доменам/рискам — в тактическом контуре агента `marketing` после [`marketing-context`](../marketing-context/SKILL.md) и [`marketing-router`](../marketing-router/SKILL.md).

## When to use

- Новое имя продукта, фичи, приложения или компании; ребрендинг.
- Подбор домена и TLD, вариации если занято.
- Согласование имени с tone of voice и позиционированием из [`app/docs/marketing/context.md`](../../../app/docs/marketing/context.md).

## When not to use (маршрутизация)

- Глубокое **GTM / ICP / positioning с нуля** — [`marketing-research-playbook`](../marketing-research-playbook/SKILL.md) и агент `marketing-researcher`.
- Только визуальная система — [`brand-visual-generator`](../brand-visual-generator/SKILL.md).
- Полная **brand story / architecture** — [`branding`](../branding/SKILL.md) (часто в паре *после* черновика имён из этого скилла).

## Делегирование

- **Веб-факты** (паттерны конкурентов, публичные данные о занятости торговых марок в юрисдикции): только через **`Task(subagent_type="researcher", ...)`** — см. [`.cursor/docs/CREATING_ASSETS.md`](../../docs/CREATING_ASSETS.md#task-delegation).
- Этот скилл **не обещает** real-time WHOIS/API: см. [references/domain-and-availability.md](references/domain-and-availability.md).

## Вход (собрать до генерации)

1. Что именуем (продукт / компания / фича) и для кого (сегмент из контекста).
2. Языки и рынки; слова и ассоциации «must / avoid».
3. Ограничения: длина, латиница vs локаль, запрет на суффиксы вроде `-ly`, обязательный `.com` и т.д.
4. Конкуренты и имена, от которых нужно отличаться.

## Стратегии генерации

Краткая матрица — в [references/naming-strategies.md](references/naming-strategies.md). Комбинируй 2–3 стратегии, затем сузь список.

## Формат выдачи (каждый кандидат)

Для **5–7** финальных кандидатов (после внутреннего отсечения грубых дублей):

1. **Name** — предлагаемое имя (и транслит/написание, если релевантно).
2. **Rationale** — связь с ценностью продукта и аудиторией.
3. **Brand fit** — как вписывается в архитектуру бренда и сообщения из контекста.
4. **Memorability** — почему запоминается и отличается от шаблонов ниши.
5. **Domain & trademark** — **эвристика**: «вероятно свободно / скорее занято / нужна проверка»; явно: *юридическая чистота не подтверждена без поиска по реестрам и консультанта*.

Затем блок **Top pick + runner-up** (1–2 строки каждый).

## Скоринг и чеклист

Используй [references/validation-and-scoring.md](references/validation-and-scoring.md): шкалы 1–10 и финальный чеклист перед рекомендацией.

## Домены и занятость

Порядок действий и честные ограничения — [references/domain-and-availability.md](references/domain-and-availability.md).

## Upstream (адаптация, не копипаст)

Практики сведены из:

- [domain-name-brainstormer](https://skills.sh/composiohq/awesome-claude-skills/domain-name-brainstormer) (composiohq/awesome-claude-skills)
- [product-name](https://skills.sh/phuryn/pm-skills/product-name) (phuryn/pm-skills)
- [brand-name-generator](https://skills.sh/shipshitdev/library/brand-name-generator) (shipshitdev/library)

Локальный канон — этот репозиторий; внешние `SKILL.md` в проект не импортировать без [`ecosystem-integrator`](../ecosystem-integrator/SKILL.md).
