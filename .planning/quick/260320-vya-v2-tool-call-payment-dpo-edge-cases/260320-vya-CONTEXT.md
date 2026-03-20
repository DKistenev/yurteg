# Quick Task 260320-vya: Подготовка датасета v2 — Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Task Boundary

Подготовить обновлённый SFT-датасет для переобучения Qwen 2.5 1.5B. Исходный датасет: `SuperPuperD/yurteg-legal-sft` на HF (635 train + 95 val). Результат: обновлённый датасет в том же репо, готовый для Axolotl.

Изменения:
1. Конвертация формата из plain JSON → Qwen-native tool call
2. Удаление поля confidence
3. Добавление payment_* полей (4 штуки) ко всем примерам
4. Генерация 50-80 DPO-пар по 5 категориям ошибок
5. Добавление edge cases: нестандартные типы документов, negative examples, OCR-мусор
6. Обновление system prompt (убрать формат-инструкции)

</domain>

<decisions>
## Implementation Decisions

### Tool Call формат
- Qwen-native формат: `<tool_call>{"name": "extract_metadata", "arguments": {...}}</tool_call>`
- Родной формат Qwen 2.5, модель видела его в pretraining
- Ollama поддерживает через chat template

### Схема tool call (13 полей, без confidence)
- document_type (string, required)
- counterparty (string|null)
- subject (string, required)
- date_signed (string|null, YYYY-MM-DD)
- date_start (string|null, YYYY-MM-DD)
- date_end (string|null, YYYY-MM-DD)
- amount (string|null)
- special_conditions (array of strings, required)
- parties (array of strings, required)
- is_template (boolean, required)
- payment_terms (string|null)
- payment_amount (number|null)
- payment_frequency (string|null, enum: monthly/quarterly/yearly/once/null)
- payment_direction (string|null, enum: income/expense/null)

### Payment_* заполнение
- Субагент Haiku читает тексты договоров из датасета и заполняет payment_* поля
- Документы без платежей (претензии, доверенности, жалобы) → все payment_* = null
- Без внешних API — всё внутри сессии Claude Code

### DPO стратегия
- 50-80 пар, 5 категорий rejected-примеров:
  1. Невалидный JSON (15 пар): unquoted strings, trailing commas, одинарные кавычки
  2. Кривые даты (15 пар): DD.MM.YYYY вместо YYYY-MM-DD, перепутанные date_signed/date_start
  3. Пустые массивы (15 пар): special_conditions=[] и parties=[] когда данные есть
  4. Краткий subject (15 пар): "Оказание услуг" vs развёрнутое описание
  5. Ошибки ФИО/падежей (15 пар): имена в косвенном падеже вместо именительного
- Генерация через субагента, формат Qwen tool call (совпадает с SFT)

### System prompt
- Убрать инструкции по формату (грамматика + tool call берут на себя)
- Оставить только смысловые правила: ФИО в именительном падеже, контрагент ≠ наша сторона, шаблоны → is_template=true

### Claude's Discretion
- Конкретная реализация скриптов конвертации
- Порядок выполнения шагов
- Формат edge cases и negative examples
- Количество дополнительных SFT-примеров для типов с 5 примерами

</decisions>

<specifics>
## Specific Ideas

- 50 из 74 типов документов имеют ровно 5 примеров — довести до 8-10
- Добавить 10-15 примеров с нестандартными типами (модель должна уметь создавать новые типы)
- Добавить 15-20 negative examples (не-юридические тексты)
- Добавить 10-15 edge cases (OCR-мусор, короткие документы)
- DPO-формат: prompt + chosen + rejected (тот же что уже есть в dpo_claude_train.jsonl)

</specifics>

<canonical_refs>
## Canonical References

- `dataset/` — локальные скрипты генерации и очистки датасета
- HF: `SuperPuperD/yurteg-legal-sft` — исходный датасет (train.jsonl, val.jsonl, dpo_claude_train.jsonl, sft_config.yaml)
- `modules/ai_extractor.py` — текущий промпт и схема полей (для совместимости)

</canonical_refs>

---

*Quick Task: 260320-vya*
*Context gathered: 2026-03-20 via discussion*
