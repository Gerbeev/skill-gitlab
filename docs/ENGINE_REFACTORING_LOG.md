# Журнал рефакторинга Python (без правок markdown-скиллов)

Скиллы (`skills/*/SKILL.md`, `workflow.md`, `step-*.md`) намеренно не трогаем, пока идёт стабилизация промптов. Меняем движок, `tools/` и `mr-impact-method/scripts/`.

## 2026-10-01 — итерация 1

| Изменение | Зачем |
| --- | --- |
| `mr_impact/index/adapters/reader_calls.py` | Общая логика edges из tree-sitter для C# и `ReadersBridgeAdapter` |
| `mr_impact/cli_dispatch.py` | Парсер и dispatch отдельно от `cli.py` (+ `tests/test_cli.py`) |
| `mr-impact-method/scripts/engine_paths.py` | Единое разрешение пути к движку для `run_engine.py` и `setup.py` |
| `tools/find_orphan_skill_references.py` | Ловит неподключённые `references/*.md` без изменения скиллов |
| `tools/quality.py` | Orphan-check `--strict` в CI-цепочке |

## 2026-10-01 — итерация 2

| Изменение | Зачем |
| --- | --- |
| `mr_impact/paths.py` (`AnalysisLayout`, `require_index_sqlite`) | Один источник путей index/graph/run/catalog |
| `mr_impact/json_io.py` | Общий `write_json` / `load_json_dict` (pipeline, MR, issue, validate, update) |
| `graph/query.load_indexed_edges` | Загрузка edges из sqlite или graph JSON через layout |
| `tests/test_paths.py` | Smoke для layout и ошибки без индекса |

## 2026-10-01 — итерация 3

| Изменение | Зачем |
| --- | --- |
| `mr/symbols_from_diff.py` | Reindex, JIL sources, diff symbols, `impact_seeds_from_diff` |
| `artifacts/contract.py` | Структурная проверка MR JSON без внешних зависимостей |
| `validate_mr_run` | Контрактные ключи поверх «валидный JSON» |
| `tests/test_symbols_from_diff.py`, `tests/test_contract.py` | Покрытие новой логики |

## 2026-10-01 — итерация 4

| Изменение | Зачем |
| --- | --- |
| `mr/reports.py` | `01`–`04` markdown + `MrMarkdownInput` |
| `mr/analyze.py` | Только JSON + вызов `write_mr_markdown_reports` |
| `tests/test_mr_reports.py` | Smoke на рендер заголовков и stale note |

## 2026-10-01 — итерация 5

| Изменение | Зачем |
| --- | --- |
| `mr/run_context.py` | Единый `MrRunContext` для JSON и markdown |
| `mr/payloads.py` | Сбор и запись MR JSON артефактов |
| `mr/analyze.py` | Оркестрация: context → payloads + reports |

**Следующие шаги:** тонкая настройка `issue/analyze` по тому же паттерну; jsonschema optional extra.
