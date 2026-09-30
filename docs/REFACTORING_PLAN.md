# План рефакторинга репозитория MR Impact

Документ описывает целевую архитектуру, приоритеты и этапы. Текущий статус реализации — [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md). Контракт движка — [reference/engine-contract.md](reference/engine-contract.md).

**Дата обзора:** 2026-10-01 · **~833** отслеживаемых файлов в git, из них **~617** — `examples/BMAD-METHOD/` (справочник, не продукт).

---

## 1. Текущая архитектура (как есть)

```text
skill-gitlab/
├── skills/                    # Источник правды: 5 скиллов + mr-impact-method + _engine
├── .github/skills/            # Копия для Copilot (setup.py, 52 файла, дублирует skills/)
├── _mr-impact/                # Runtime после setup (gitignore; копия engine + scripts)
├── docs/reference/            # Контракт, глоссарий, спецификация
├── tools/                     # quality.py, validate_skills, validate_file_refs
├── examples/BMAD-METHOD/      # Вендорный референс BMAD (не в CI engine.yml)
└── .repository-analysis/      # Индекс/граф/run (частично gitignore)
```

**Поток выполнения:** Copilot → `SKILL.md` → `render_skill.py` → снимок в `_mr-impact/render/` → шаги → `run_engine.py` → `mr_impact` CLI.

**Сильные стороны:** чёткое разделение детерминированного движка и LLM-скиллов; единый `tools/quality.py`; контракт артефактов; тесты на fixtures.

**Главные боли:**

| Проблема | Эффект |
| --- | --- |
| Двойное дерево скиллов (`skills/` + `.github/skills/`) | Риск рассинхрона, лишние диффы в PR |
| Копия движка в `_mr-impact/engine/` | Дублирование на диске; путаница «где править» |
| Крупный `examples/BMAD-METHOD/` | Раздувает клон; CI не использует |
| Размытие документации (`TASK_STATEMENT` vs `V1_SCOPE` vs `engine-contract`) | Сложно понять «что обязательно» |
| Общие `references/` копируются в каждый скилл setup'ом | 5× одинаковых `workflow-discipline.md` и т.д. |
| Мёртвые/локальные файлы в git (см. [DELETION_CANDIDATES.md](DELETION_CANDIDATES.md)) | Шум в истории |

---

## 2. Целевое состояние (кратко)

1. **Один источник правды для скиллов** — только `skills/`; `.github/skills/` либо генерируется в CI/setup и не коммитится, либо коммитится автоматически одним job (политика на выбор, см. фазу A).
2. **Один источник правды для Python** — только `skills/_engine/`; `_mr-impact/engine/` всегда производный (уже так по замыслу, усилить документацией и pre-commit).
3. **Документация в три слоя:** контракт (`engine-contract`) → продуктовая граница (`V1_SCOPE`) → полная спецификация (`TASK_STATEMENT`); корневой README — только установка и сценарии.
4. **Референс BMAD** — submodule, отдельная ветка или ссылка на upstream (не 600+ файлов в основном дереве).
5. **Скиллы:** тонкий `SKILL.md`, без дублирования правил движка; общие дисциплины — один файл + `rendered()` из `mr-impact-method` (без физических копий в пяти папках).

---

## 3. Фазы рефакторинга

### Фаза A — Гигиена репозитория (низкий риск)

**Цель:** убрать мусор и зафиксировать правила генерации.

| # | Задача | Критерий готовности |
| --- | --- | --- |
| A1 | Удалить кандидатов из [DELETION_CANDIDATES.md](DELETION_CANDIDATES.md) (раздел «уверенно») | `python tools/quality.py` зелёный |
| A2 | Добавить в `.gitignore`: `.obsidian/`, при необходимости локальные IDE-артефакты | Файлы не возвращаются в git |
| A3 | Подключить `evidence-rules.md` в `analyze-issue` (step-01 или engine step) **или** удалить файл | Нет orphan `references/` (скрипт проверки в фазе D) |
| A4 | Документировать: «править только `skills/_engine`» в CONTRIBUTING или `skills/README.md` | Один абзац в README/skills |

**Решение по `.github/skills/` (выбрать одно):**

- **A5a (рекомендуется для форков):** оставить коммит копий, но добавить CI-шаг «sync check» — `setup.py` + `git diff --exit-code .github/skills` после quality.
- **A5b (минимальный git):** убрать `.github/skills/` из git; в README — обязательный setup перед Copilot; CI всё равно гоняет setup.

---

### Фаза B — Слой скиллов и setup

**Цель:** меньше копипасты, проще сопровождать пять команд.

| # | Задача | Детали |
| --- | --- | --- |
| B1 | Общие `references/` не копировать в каждый скилл | В `workflow.md`: `{{ rendered("../../mr-impact-method/references/workflow-discipline.md") }}` или аналог в `render_skill` (проверить пути в снимке) |
| B2 | Упростить `install_shared_references` в `setup.py` | Удалить цикл копирования после B1 |
| B3 | Аудит BMAD-хвостов | `resolve_config.py` не вызывается ни одним шагом MR Impact — вынести в `scripts/dev/` или удалить из `SCRIPT_NAMES` с пометкой в CHANGELOG |
| B4 | Единый `setup_check` в начале каждого workflow | Уже частично есть; выровнять сообщения и ссылки на `help/common-blockers.md` |

---

### Фаза C — Движок `mr_impact`

**Цель:** модули с явными границами, проще тестировать и расширять адаптеры.

| # | Область | Направление |
| --- | --- | --- |
| C1 | `index/adapters` vs `readers/` | Документировать матрицу «язык → adapter → reader» в `skills/_engine/README.md`; убрать дубли логики SQL literals между `csharp` и `readers_bridge` |
| C2 | `graph/query.py` + `nearest_runtime.py` | Единая точка входа «impact + QA paths» для `mr/analyze.py` и `issue/analyze.py` |
| C3 | `artifacts/validate.py` | Схемы JSON (или jsonschema) рядом с контрактом; версии `issue-update.json` v2 — в `engine-contract` |
| C4 | Legacy CLI | После периода deprecation удалить `index-repository` / `run_deep_index` из публичного CLI (оставить внутренний вызов create-index + create-graph) |
| C5 | Упаковка | Опционально: один `pyproject.toml` в корне монорепо вместо только `skills/_engine` (uv/pip — по [python-setup.md](reference/python-setup.md)) |

---

### Фаза D — Документация и спецификация

| # | Задача |
| --- | --- |
| D1 | В `docs/README.md` явная иерархия: contract → V1 → TASK_STATEMENT |
| D2 | Сократить дубли путей `.github/skills` vs `skills` в TASK_STATEMENT (одна колонка «источник» / «после setup») |
| D3 | Объединить или пометить устаревшими фрагменты MVP_TASK_IMPROVEMENTS, если они уже реализованы (ссылка на галочки DEVELOPMENT_PLAN) |
| D4 | Скрипт `tools/find_orphan_references.py` (логика из разового анализа) в CI |

---

### Фаза E — `examples/BMAD-METHOD`

| # | Вариант | Плюсы / минусы |
| --- | --- | --- |
| E1 | Git submodule на тег BMAD | Малый основной репо; нужен `git submodule update` |
| E2 | Удалить дерево, ссылка в README на github.com/bmad-code-org/BMAD-METHOD | Минимальный размер; офлайн-референс пропадает |
| E3 | Оставить как есть | Нулевая миграция; тяжёлый клон |

**Рекомендация:** E1 или E2 после согласования с командой; CI `engine.yml` не затрагивается.

---

### Фаза F — Инфраструктура CI

| # | Задача |
| --- | --- |
| F1 | Триггер CI на `docs/reference/engine-contract.md` при изменении контракта |
| F2 | Кэш pip в Actions |
| F3 | Отчёт coverage по `skills/_engine` (опционально) |
| F4 | Pre-commit: запрет коммита `__pycache__`, `.obsidian` |

---

## 4. Порядок выполнения (рекомендуемый)

```text
A (гигиена + политика .github/skills)
  → B (скиллы/setup)
  → D1–D2 (доки, параллельно с B)
  → C (движок, по приоритету стека: JIL/SQL/C# у вас уже в Phase 3 DEVELOPMENT_PLAN)
  → E (BMAD, отдельное решение)
  → F (CI polish)
```

Не смешивать в одном PR: удаление файлов (A) и смена модели копирования references (B).

---

## 5. Метрики успеха

- `python tools/quality.py` без ручного setup на чистом clone (уже цель quality.py).
- Нулевой `git diff` после `setup.py` для `.github/skills/` (если выбран A5a).
- Нет orphan-файлов в `skills/*/references/`.
- Новый разработчик читает ≤3 документа перед первым PR: root README, `engine-contract`, `skills/README.md`.

---

## 6. Связанные артефакты

| Документ | Назначение |
| --- | --- |
| [DELETION_CANDIDATES.md](DELETION_CANDIDATES.md) | Что можно удалить и с какой уверенностью |
| [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) | Чеклист фич (не структурный рефакторинг) |
| [reference/V1_SCOPE.md](reference/V1_SCOPE.md) | Граница MVP |
| [reference/TASK_STATEMENT.md](reference/TASK_STATEMENT.md) | Полная спецификация |
