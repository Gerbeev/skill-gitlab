# Как используется `examples/BMAD-METHOD` и паритет с MR Impact

Папка **не является зависимостью** продукта: `tools/quality.py` и `.github/workflows/engine.yml` её не вызывают. Это **закладной референс** архитектуры BMAD (тонкий Copilot skill → `render_skill` → снимок workflow → шаги → скрипты в `_bmad/`).

Ссылки из нашего репозитория: корневой [README.md](../../README.md), [GLOSSARY.md](GLOSSARY.md), [skills/README.md](../../skills/README.md), [tools/skill-validator.md](../../tools/skill-validator.md) (полный каталог правил — в BMAD).

---

## Что в BMAD реально «держит» скиллы

| Механизм | Где в BMAD | У MR Impact |
| --- | --- | --- |
| Тонкий `SKILL.md` | `examples/BMAD-METHOD/skills/*/SKILL.md` | `skills/*/SKILL.md` → то же |
| `render_skill.py` | `skills/bmad/scripts/` → `_bmad/scripts/` | `skills/mr-impact-method/scripts/` → `_mr-impact/scripts/` |
| `setup.py` | Синхронизация скиллов, runtime, config | `skills/mr-impact-method/scripts/setup.py` → `.github/skills/` + `_mr-impact/` |
| Манифест модуля | `bmod.toml` (skills, knowledge, required_skills) | `skills/mr-impact-method/bmod.toml` (только список пяти скиллов) |
| `customize.toml` | Пер-сkill + `_bmad/custom/` | `_mr-impact/custom/<skill>.toml` |
| Валидация скиллов | `tools/validate_skills.py` (+ manifests, pre-commit) | `tools/validate_skills.py` (адаптация SKILL-01–08) |
| Quality gate | `uv` + pre-commit + docs-site | `python tools/quality.py` (engine + setup + validate) |
| Конфиг CLI | `resolve_config.py` в workflow многих BMAD-скиллов | Конфиг мержится **внутри** `render_skill.py`; CLI `resolve_config.py` — опционально для отладки |

Итог: **поддержка «как у BMAD» для наших задач уже есть** в `skills/` + `tools/`; папка `examples/` нужна людям и авторам, которые сравнивают с upstream, а не рантайму Copilot.

---

## Что в BMAD есть, а нам не нужно копировать

- **Полный каталог скиллов** (PRD, party-mode, build-auto, …) — другой продукт.
- **`uv` / docs-site / Astro** — отдельный сайт документации BMAD.
- **`validate_manifests.py`** — граф зависимостей между десятками `bmod.toml`; у нас один модуль и пять скиллов.
- **Обновление с GitHub** (`update_source` в bmod) — у нас `update_source = "file:skills"`.

Дублировать BMAD setup (2400+ строк) в MR Impact **не имеет смысла** — достаточно держать референс и точечно переносить идеи (см. ниже).

---

## Имеет смысл усилить (по мотивам BMAD)

| Идея из BMAD | Зачем нам | Статус / действие |
| --- | --- | --- |
| Проверка, что каждый `references/*.md` подключён из workflow/steps | Ловит пропуски вроде бывшего orphan `evidence-rules.md` | Подключено в `analyze-issue`; можно добавить `tools/find_orphan_references.py` в CI ([REFACTORING_PLAN.md](../REFACTORING_PLAN.md) D4) |
| `validate_file_refs.py` | Битые пути в markdown/TOML | Уже есть в `tools/quality.py` |
| Smoke `setup.py --status` | Copilot видит все пять скиллов | Уже в `quality.py` |
| CI check: `setup` + чистый `git diff .github/skills` | Нет рассинхрона source vs Copilot | Рекомендация фазы A5a в [REFACTORING_PLAN.md](../REFACTORING_PLAN.md) |
| Shared references без копирования в 5 папок | Меньше дублирования `workflow-discipline.md` | Фаза B рефакторинга |

---

## Orphan `evidence-rules.md` (исправление)

Файл был в репозитории, но **не был подключён к workflow** — это ошибка сопровождения, а не лишний markdown.

Сейчас:

- `skills/analyze-issue/step-01-prepare-input.md` — явное чтение `references/evidence-rules.md`
- `skills/analyze-issue/customize.toml` — факт в `persistent_facts`

После правок скиллов: `python skills/mr-impact-method/scripts/setup.py --project-root .`

---

## Когда трогать `examples/BMAD-METHOD`

- Сравнить новый паттерн BMAD (например, изменение `render_skill.py`) с нашей копией в `skills/mr-impact-method/scripts/`.
- Не импортировать Python-пути из `examples/` в продуктовый код.

Вынести в submodule — только если размер клона критичен ([REFACTORING_PLAN.md](../REFACTORING_PLAN.md), фаза E).
