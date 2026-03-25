---
id: SEED-002
status: dormant
planted: 2026-03-25
planted_during: v0.8.1 UI Polish
trigger_when: после UI Polish, когда карточка документа и шаблоны стабилизировались
scope: Large
---

# SEED-002: Векторная система шаблонов и версий документов

## Why This Matters

Две ключевые фичи для юриста:

1. **Версии:** Автоматически находить разные версии одного документа (через embeddings), группировать в карточке, давать скачать redline с отслеживанием правок. Юрист видит: «вот текущий договор, вот предыдущая версия, вот что изменилось».

2. **Шаблоны:** Юрист загружает эталонный договор → система через векторы находит все похожие документы в реестре → для каждого показывает отклонения от эталона → можно скачать redline. Не ручной подбор, а автопоиск.

Без этого кнопки «Найти шаблон» и «Сравнить →» в UI — пустышки.

## When to Surface

**Trigger:** После завершения v0.8.1 UI Polish — когда карточка документа стабильна и есть куда показывать результаты

This seed should be presented during `/gsd:new-milestone` when the milestone scope matches:
- Работа с шаблонами документов
- Версионирование / diff / сравнение
- AI/NLP/векторный поиск
- Бэкенд-фичи для реестра

## Scope Estimate

**Large** — полный milestone:
- Бэкенд: sentence-transformers embeddings (уже есть `compute_embedding` в version_service.py), cosine similarity поиск, автогруппировка версий
- Redline: `diff_versions()` уже есть, но сравнивает subject а не полный текст — нужно переделать на extracted text
- Шаблоны: `match_template()` и `review_against_template()` существуют в review_service.py, но нужен векторный поиск + redline generation
- UI: wiring кнопок «Найти шаблон», «Сравнить →», модал с redline preview
- Тесты: E2E flow загрузка шаблона → поиск → сравнение → redline

## Breadcrumbs

### Версии (уже частично реализовано)
- `services/version_service.py` — `compute_embedding()`, `find_version_match()`, `link_versions()`, `get_version_group()`, `diff_versions()`
- `modules/database.py` — таблица `document_versions` (FK to contracts), таблица `embeddings`
- `app/pages/document.py` — секция «История версий» с таймлайном и ссылками «Сравнить →»
- `app/main.py` — route `/download/redline/{id1}/{id2}` (существует, но сравнивает subject а не текст)

### Шаблоны (уже частично реализовано)
- `services/review_service.py` — `match_template()`, `review_against_template()`, CRUD для шаблонов
- `modules/database.py` — таблица `templates`
- `app/pages/templates.py` — UI шаблонов (карточки, CRUD)
- `app/pages/document.py` — секция «Проверка по шаблону» с кнопками «Найти» и «Добавить»

### Embeddings
- `sentence-transformers` в requirements.txt
- `compute_embedding()` в version_service.py — truncates text to 8000 chars
- `_cosine_sim()` — нормализованное сравнение

## Notes

Бэкенд для версий и шаблонов уже написан в v0.4, но:
1. Redline сравнивает `subject` (1-2 предложения), а не полный текст — бесполезно
2. Векторный поиск шаблонов не wired к UI кнопке «Найти»
3. Автогруппировка версий работает при загрузке, но не при ручном добавлении
4. Нет UI для просмотра redline diff (только скачивание .docx)

Это milestone-уровневая работа: бэкенд рефакторинг + UI wiring + тесты.
