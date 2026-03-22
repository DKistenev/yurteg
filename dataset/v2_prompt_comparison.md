# Сравнение промптов v2 — борьба с code-switching

Модель: `yurteg-v2` | Дата: 2026-03-21

Метрика: кол-во английских слов (3+ букв) в JSON-ответе, кроме enum-значений (monthly/once/quarterly/yearly/income/expense).

## Таблица результатов

| Документ | Вариант A | Вариант B | Вариант C | Лучший |
|----------|-----------|-----------|-----------|--------|
| `03_шаблон.txt` | 34 | 24 | 27 | **B** |
| `05_трудовой.txt` | 17 | 30 | 54 | **A** |
| `10_ocr_мусор.txt` | 19 | 51 | 40 | **A** |
| `11_не_юридический.txt` | 15 | 70 | 35 | **A** |
| `29_nda.txt` | 24 | 17 | 18 | **B** |
| `30_иностранный.txt` | 29 | 30 | 30 | **A** |
| `35_смешанный.txt` | 20 | 24 | 27 | **A** |
| `40_маркетинг.txt` | 25 | 27 | 37 | **A** |
| `57_пустой_шаблон.txt` | 25 | 24 | 25 | **B** |
| `33_оферта.txt` | 17 | 35 | 33 | **A** |
| **ИТОГО** | **225** | **332** | **326** | **A** |

## Найденные английские слова (примеры)

### `03_шаблон.txt`

- Вариант A: `document, type, ErrorResponse, counterparty, isher, subject, supply, amount, special, conditions`
- Вариант B: `document, type, SpecialCondition, counterparty, subject, amount, special, conditions, parties, template`
- Вариант C: `document, type, Percentage, counterparty, client, subject, amount, default, special, conditions`

### `05_трудовой.txt`

- Вариант A: `document, type, counterparty, subject, amount, special, conditions, parties, template, payment`
- Вариант B: `document, type, Error, document, multipart, request, counterparty, subject, PARTIES, amount`
- Вариант C: `document, type, Contract, counterparty, Grygoriy, Geynichovich, Tumanov, subject, Performing, agricultural`

### `10_ocr_мусор.txt`

- Вариант A: `document, type, counterparty, subject, amount, special, conditions, applicable, parties, olg`
- Вариант B: `document, type, contract, counterparty, subject, amount, What, the, price, the`
- Вариант C: `document, type, ania, counterparty, subject, ickye, usczluyeniya, avtotoportnyx, sredstv, avtomobili`

### `11_не_юридический.txt`

- Вариант A: `document, type, counterparty, subject, amount, special, conditions, ERy, ERy, clusions`
- Вариант B: `document, type, document, counterparty, subject, director, corporate, development, investor, relations`
- Вариант C: `document, type, counterparty, subject, Moscow, State, University, amount, value, not`

### `29_nda.txt`

- Вариант A: `document, type, vested, interest, counterparty, subject, vested, interest, CEO, amount`
- Вариант B: `document, type, counterparty, subject, amount, special, conditions, parties, template, payment`
- Вариант C: `document, type, counterparty, subject, amount, name, the, agreement, special, conditions`

### `30_иностранный.txt`

- Вариант A: `document, type, counterparty, SoftWare, Solutions, GmbH, subject, DataBridge, Enterprise, amount`
- Вариант B: `document, type, metadata, counterparty, subject, DataBridge, Enterprise, amount, EUR, special`
- Вариант C: `document, type, counterparty, subject, DataBridge, Enterprise, amount, EUR, special, conditions`

### `35_смешанный.txt`

- Вариант A: `document, type, counterparty, subject, amount, special, conditions, incl, till, servicua`
- Вариант B: `document, type, counterparty, subject, amount, special, conditions, incl, parties, template`
- Вариант C: `document, type, counterparty, subject, amount, special, conditions, lost, profit, upply`

### `40_маркетинг.txt`

- Вариант A: `document, type, counterparty, subject, commerce, tokens, amount, special, conditions, onderletty`
- Вариант B: `document, type, GTD, counterparty, subject, focus, amount, bytes, special, conditions`
- Вариант C: `document, type, counterparty, subject, eting, amount, special, conditions, upfront, before`

### `57_пустой_шаблон.txt`

- Вариант A: `document, type, counterparty, subject, amount, special, conditions, document, delivery, parties`
- Вариант B: `document, type, Requisites, counterparty, subject, amount, special, conditions, parties, template`
- Вариант C: `document, type, counterparty, subject, amount, crypto, dollar, special, conditions, parties`

### `33_оферта.txt`

- Вариант A: `document, type, counterparty, subject, amount, special, conditions, parties, template, payment`
- Вариант B: `document, type, metadata, extraction, counterparty, subject, amount, special, terms, special`
- Вариант C: `document, type, counterparty, irmName, subject, inheritance, apapapapap, amount, crypto, amount`

## Анализ

**Лучший вариант: A** — 225 английских слов суммарно
**Второй: C** — 326 слов
**Худший: B** — 332 слов

- Вариант A («Жёсткие правила» — запрет + подробные инструкции): **225** англ. слов
- Вариант B («Минимальный» — только одна фраза о русском языке): **332** англ. слов
- Вариант C («С примером» — пример правильного ответа): **326** англ. слов

## Рекомендация для финального промпта

Использовать **Вариант A** как основу. Явный запрет с перечислением правил даёт модели чёткие ограничения. Можно дополнить примером из Варианта C для укрепления паттерна.

### Комбинированный финальный промпт (рекомендуется)

```
Извлеки метаданные из текста юридического документа. Все значения ТОЛЬКО на русском языке.

Пример правильного ответа:
document_type: "Договор оказания услуг"
subject: "Оказание консультационных услуг по вопросам налогообложения"
special_conditions: ["Неустойка 0,1% за каждый день просрочки"]

Правила:
- document_type: "Договор займа", "Договор поставки", "Трудовой договор" и т.д.
- amount: "2 000 000 руб."
- payment_frequency: "monthly"/"once"/"quarterly"/"yearly"
- payment_direction: "income"/"expense"

Текст документа:
{text}
```