---
name: capability-architecture
description: >-
  Проектирование систем вокруг capabilities, границ, контрактов и слоёв: снижение coupling, явные trust boundaries,
  observability. Use when планируешь крупную фичу, рефактор модулей, контракты между пакетами; в паре с
  [architecture-principles](../architecture-principles/SKILL.md) для code review.
---

# Capability Architecture (локальная адаптация)

## Связь с architecture-principles

- **[architecture-principles](../architecture-principles/SKILL.md)** — чеклист Level 2 для агента `reviewer-senior` (оценка решений в уже написанном коде).
- **capability-architecture** (этот скилл) — **ранний** язык для `planner` / design specs: capability map, границы, контракты до или вместе с реализацией.
- Не дублируй длинные чеклисты: для review кода ссылайся на `architecture-principles`; для декомпозиции домена — на `references/` ниже.

## Core Rules

Всегда разделяй:

- what the system does
- how it is displayed
- how it is stored
- how it is called

## Workflow

When designing or refactoring architecture:

1. Identify business capabilities
2. Define module boundaries per capability
3. Establish explicit contracts between modules
4. Define security and trust boundaries per capability
5. Define observability boundaries per capability
6. Assign responsibilities by layer
7. Isolate external systems behind adapters
8. Prevent cross-layer and cross-module leakage
9. Compose the system from capability modules

## Non-Negotiable Rules

- Organize by capabilities, not technical artifact type.
- Keep dependency direction inward toward domain logic.
- Keep presentation and transport layers thin.
- Keep infrastructure replaceable through adapters.
- Communicate between modules through contracts only.
- Introduce shared abstractions only after reuse is proven.
- Enforce authorization at capability entry points.
- Validate untrusted input at trust boundaries.
- Classify sensitive data and secrets; secret handling in infrastructure.
- Capability-level observability at entry, success, and failure boundaries.
- Structured logs, correlation context, no secret leakage.

## Делегирование

Оркестрация правок кода — через **`Task(subagent_type="worker"|"refactor", ...)`**; этот скилл не отменяет канон [CREATING_ASSETS](../../docs/CREATING_ASSETS.md).

## Output Contract

- Clear capability ownership.
- Boundaries and contracts for interactions.
- Layer responsibility split.
- No framework/DB leakage into domain logic.
- Anti-pattern risks + mitigations.
- Trust boundaries and authz expectations where relevant.
- Observability expectations (events, metrics, traces, correlation IDs) where relevant.

## Reference Index

- [references/architecture-principles.md](references/architecture-principles.md) — принципы разделения (внутри пакета; не путать с skill `architecture-principles`).
- [references/layering-model.md](references/layering-model.md)
- [references/capability-modules.md](references/capability-modules.md)
- [references/boundary-contracts.md](references/boundary-contracts.md)
- [references/coupling-rules.md](references/coupling-rules.md)
- [references/reuse-guidelines.md](references/reuse-guidelines.md)
- [references/anti-patterns.md](references/anti-patterns.md)
- [references/security.md](references/security.md)
- [references/observability.md](references/observability.md)
- [references/implementation-process.md](references/implementation-process.md)

## When To Use This Skill

- Новая подсистема / сервисные границы.
- Крупный рефактор и разрез модулей.
- Усиление security/observability на границах capabilities.
- Подготовка спеки в `.cursor/plans/` перед `worker`.
