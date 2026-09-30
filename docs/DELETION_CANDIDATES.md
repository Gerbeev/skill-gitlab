# Кандидаты на удаление

Список составлен по статическому анализу репозитория (октябрь 2026): поиск ссылок в `skills/`, `docs/`, `tools/`, `.github/workflows/`. Перед удалением прогоните `python tools/quality.py`.

Уровни уверенности:

- **Уверенно** — нет ссылок из продукта/CI или артефакт сборки; удаление не ломает контракт.
- **Высокая** — не используется шагами скиллов, но может быть полезен вручную; удалять после короткой проверки.
- **Не удалять** — часто путают с мусором, но нужны для работы.

---

## Уверенно удалить (или убрать из git)

### Локальные / генерируемые (не должны быть в истории)

| Путь | Причина |
| --- | --- |
| `**/__pycache__/**`, `**/*.pyc` | Кэш Python; уже в `.gitignore` |
| `.pytest_cache/**` | Кэш тестов |
| `_mr-impact/**` (весь каталог на диске) | Создаётся `skills/mr-impact-method/scripts/setup.py`; в `.gitignore` |
| `**/_lib/**` (tree-sitter под readers) | Опциональная установка; в `.gitignore` |
| `.repository-analysis/run/**` | Эфемерные артефакты скиллов; в `.gitignore` |

### Отслеживаются в git, но не используются продуктом

| Путь | Причина |
| --- | --- |
| `.obsidian/app.json` | Конфиг Obsidian; **0** ссылок из кода/доков продукта |
| `.obsidian/appearance.json` | То же |
| `.obsidian/core-plugins.json` | То же |
| `.obsidian/workspace.json` | То же |

**Действие:** `git rm -r .obsidian`, добавить `.obsidian/` в `.gitignore`.

### Orphan-файлы скиллов

Ранее: `evidence-rules.md` не был подключён — **исправлено** (см. [bmad-method-reference.md](reference/bmad-method-reference.md)). Markdown-референсы скиллов **не удалять** без проверки wiring.

---

## Высокая уверенность (проверить, затем удалить или перенести)

| Путь | Причина | Проверка |
| --- | --- | --- |
| `skills/mr-impact-method/scripts/resolve_config.py` | Ни один `step-*.md` / `SKILL.md` MR Impact не вызывает CLI; конфиг резолвится внутри `render_skill.py` | Поиск по личным скриптам/докам команды; при отсутствии — убрать из `SCRIPT_NAMES` в `setup.py` |
| Копия `resolve_config.py` в `_mr-impact/scripts/` | Производная от setup | Исчезнет после пересборки runtime |

| Дублирующий контент в пяти скиллах | `workflow-discipline.md`, `run-cleanup.md`, … | Не «удаление», а рефакторинг: один источник в `mr-impact-method/references/` (см. [REFACTORING_PLAN.md](REFACTORING_PLAN.md) фаза B) |

---

## Не удалять (частые ошибки)

| Путь | Почему нужен |
| --- | --- |
| `.github/skills/**` | Точка входа Copilot; синхронизируется из `skills/`, но **используется** без повторного setup у многих пользователей |
| `skills/**` (кроме явных orphan) | Источник правды для скиллов и движка |
| `examples/BMAD-METHOD/**` | Не в CI движка, но **упоминается** в README, GLOSSARY, `skills/README.md` как референс архитектуры |
| `.repository-analysis/catalog/boundary-catalog.json` | Сид из `boundary-catalog.example.json`; используется boundary-hints в MR |
| `skills/*/bmod.toml` | Список скиллов для `setup.py` / `bmod.toml` модуля |
| `docs/reference/TASK_STATEMENT.md` | Большой, но продуктовая спецификация |

---

## Опционально (политика репозитория, не «мусор»)

| Путь | Комментарий |
| --- | --- |
| `examples/BMAD-METHOD/**` (~617 файлов) | Можно **вынести** (submodule/ссылка), но не «неиспользуемый код» — это закладной референс |
| Весь `.github/skills/` из git | Возможно при политике «только setup» ([REFACTORING_PLAN.md](REFACTORING_PLAN.md) A5b); это рефакторинг, не очистка |

---

## Команды для безопасной очистки локально

```powershell
# Только генерируемое (не трогает git-tracked файлы)
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue _mr-impact, .repository-analysis\run
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force

# После согласования — Obsidian из git
git rm -r .obsidian
```

После удаления orphan evidence-rules и правки `.gitignore`:

```powershell
python skills/mr-impact-method/scripts/setup.py --project-root .
python tools/quality.py
```
