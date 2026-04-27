---
name: md-compressor
description: >-
  Сжимает Markdown до меньшего контекста, сохраняя факты и intent. Use when нужны dense handoff notes,
  сжатие verbose черновиков под `.cursor/`; opt-in — не для security/Task канона без отдельного review.
---

# MD Compressor (локальная адаптация)

## Core Rules

1. **Facts are immutable** — never change decisions, requirements, constraints, numbers, or references.
2. **Compression over style** — remove filler, hedging, rhetorical text first.
3. **Abbreviate** — по [references/abbreviation-map.md](references/abbreviation-map.md); не сокращай `Task`, `subagent_type`, имена файлов.
4. **Profiles** — `standard` по умолчанию; `ultra` только по явному запросу.
5. **Scanability** — lists, compact headings, short clauses.
6. **No semantic drift** — if shortening risks meaning change, keep the longer form.

## Запреты (this repo)

- Не сжимай [CREATING_ASSETS.md](../../docs/CREATING_ASSETS.md) (кроме явного поручения + human review): там канонические таблицы и запреты.
- Не трогай строки CSV; для таблиц — не применяй «ultra».

## Workflow

1. Parse source; identify factual statements.
2. Remove non-factual prose and redundancy.
3. Compact list-first structures.
4. Abbreviation map + punctuation policy.
5. [references/quality-checklist.md](references/quality-checklist.md).

## Output Contract

- Valid Markdown; preserve heading hierarchy unless lossless.
- Keep links, paths, command literals, code blocks intact.
- Header: `Profile: standard` or `Profile: ultra`.

## Reference Index

- [references/compression-workflow.md](references/compression-workflow.md)
- [references/abbreviation-map.md](references/abbreviation-map.md)
- [references/symbol-and-punctuation-policy.md](references/symbol-and-punctuation-policy.md)
- [references/quality-checklist.md](references/quality-checklist.md)

## When To Use This Skill

- Длинные планы в `.cursor/plans/`, handoff пакеты, черновики до коммита.
- Не как глобальное правило always-on.
