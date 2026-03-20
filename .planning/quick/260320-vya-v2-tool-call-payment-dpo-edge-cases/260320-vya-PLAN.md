---
phase: quick
plan: 260320-vya
type: execute
wave: 1
depends_on: []
files_modified:
  - dataset/v2_transform.py
  - dataset/v2_generate_dpo.py
  - dataset/v2_upload.py
autonomous: true
requirements: [V2-TOOLCALL, V2-PAYMENT, V2-DPO, V2-EDGE]

must_haves:
  truths:
    - "Все SFT-примеры в Qwen tool call формате с 13 полями (без confidence)"
    - "payment_* поля заполнены субагентом Haiku на основе текста контракта"
    - "50-80 DPO-пар в 5 категориях ошибок"
    - "Edge cases: нестандартные типы, negative examples, OCR-мусор"
    - "Датасет загружен на HF SuperPuperD/yurteg-legal-sft"
  artifacts:
    - path: "dataset/v2_transform.py"
      provides: "Скачивание HF + конвертация SFT в tool call + payment_* аннотация"
    - path: "dataset/v2_generate_dpo.py"
      provides: "Генерация DPO-пар + edge cases"
    - path: "dataset/v2_upload.py"
      provides: "Загрузка v2 на HuggingFace"
  key_links:
    - from: "dataset/v2_transform.py"
      to: "HuggingFace API"
      via: "huggingface_hub download"
      pattern: "hf_hub_download|snapshot_download"
    - from: "dataset/v2_generate_dpo.py"
      to: "dataset/v2_transform.py"
      via: "reads transformed train.jsonl"
      pattern: "v2_train.jsonl"
---

<objective>
Подготовить датасет v2 для дообучения Qwen 2.5 1.5B: конвертировать в tool call формат, добавить payment_* поля через Haiku-субагент, сгенерировать 50-80 DPO-пар, добавить edge cases, загрузить на HF.

Purpose: Текущий датасет v1 использует plain JSON формат и не содержит payment_* полей. Для v2 нужен нативный Qwen tool call формат, расширенная схема и больше DPO-пар для улучшения качества модели.
Output: Обновлённый датасет на HuggingFace с train/val/dpo файлами в tool call формате.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260320-vya-v2-tool-call-payment-dpo-edge-cases/260320-vya-CONTEXT.md
@dataset/prepare_dataset.py
@dataset/sft_config.yaml
@dataset/dpo_config.yaml
@modules/ai_extractor.py (lines 29-108 — SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, schema)

<interfaces>
<!-- Текущий формат SFT на HF (train.jsonl): -->
```json
{"messages": [
  {"role": "system", "content": "..."},
  {"role": "user", "content": "Извлеки метаданные...\nТекст документа:\n{text}"},
  {"role": "assistant", "content": "{\"document_type\": ..., \"confidence\": 0.92, ...}"}
]}
```

<!-- Текущий формат DPO на HF (dpo_claude_train.jsonl): -->
```json
{"prompt": [...messages...], "chosen": [...messages...], "rejected": [...messages...]}
```

<!-- Целевой формат SFT v2 (Qwen tool call): -->
```json
{"messages": [
  {"role": "system", "content": "Ты — юрист-аналитик. Правила: ФИО в именительном, контрагент != наша сторона, шаблоны → is_template=true..."},
  {"role": "user", "content": "Извлеки метаданные из текста юридического документа.\n\nТекст документа:\n{text}"},
  {"role": "assistant", "content": "<tool_call>{\"name\": \"extract_metadata\", \"arguments\": {\"document_type\": \"...\", ...13 полей без confidence...}}</tool_call>"}
]}
```

<!-- 13 полей целевой схемы (без confidence): -->
document_type (string), counterparty (string|null), subject (string),
date_signed (string|null), date_start (string|null), date_end (string|null),
amount (string|null), special_conditions (array), parties (array),
is_template (boolean),
payment_terms (string|null), payment_amount (number|null),
payment_frequency (string|null, enum: monthly/quarterly/yearly/once/null),
payment_direction (string|null, enum: income/expense/null)

<!-- HF credentials: -->
Token: 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
Repo: SuperPuperD/yurteg-legal-sft
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Скрипт трансформации SFT — скачать, конвертировать, аннотировать payment_*</name>
  <files>dataset/v2_transform.py</files>
  <action>
Создать dataset/v2_transform.py, который:

1. **Скачивает датасет с HF** через huggingface_hub:
   - `pip install huggingface_hub` если нет
   - Скачать train.jsonl и val.jsonl из SuperPuperD/yurteg-legal-sft
   - Токен: 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

2. **Конвертирует каждый пример в Qwen tool call формат:**
   - Парсит assistant content (сейчас plain JSON)
   - Удаляет поле `confidence`
   - Добавляет payment_terms=null, payment_amount=null, payment_frequency=null, payment_direction=null (заглушки, Haiku заполнит ниже)
   - Оборачивает в `<tool_call>{"name": "extract_metadata", "arguments": {...}}</tool_call>`
   - Обновляет system prompt — убрать формат-инструкции (JSON, confidence), оставить только смысловые:
     ```
     Ты — юрист-аналитик. Извлеки метаданные из юридического документа.

     Правила:
     1. Маски анонимизации ([ФИО_1], [ТЕЛЕФОН_1]) — используй как есть
     2. Отсутствующую информацию ставь null
     3. Даты строго YYYY-MM-DD
     4. ФИО в именительном падеже: "Иванов Иван Иванович"
     5. Формат ИП: "ИП Фамилия Имя Отчество"
     6. Контрагент — ДРУГАЯ сторона, не наша (Фокина/Файзулина/БУП/Digital Church)
     7. Шаблоны (пустые поля _____) → is_template=true, counterparty=null, parties=[]
     ```
   - Обновляет user prompt — убрать "Верни JSON с полями...", оставить: "Извлеки метаданные из текста юридического документа.\n\nТекст документа:\n{text}"

3. **Аннотация payment_* через Haiku-субагента:**
   - Для каждого примера: извлечь текст контракта из user message
   - Отправить в Claude Haiku (через anthropic SDK, ключ из ANTHROPIC_API_KEY env) с промптом:
     ```
     Прочитай текст юридического документа и определи платёжные условия.
     Верни JSON с 4 полями:
     - payment_terms (string|null): описание порядка оплаты ("ежемесячно до 5-го числа") или null
     - payment_amount (number|null): сумма одного платежа (число без валюты) или null
     - payment_frequency (string|null): "monthly", "quarterly", "yearly", "once" или null
     - payment_direction (string|null): "income" (деньги от контрагента) или "expense" (платим мы) или null

     Если документ не связан с платежами (претензия, доверенность, жалоба, приказ) — все поля null.
     Верни ТОЛЬКО JSON, без текста.
     ```
   - Батчить по 5-10 запросов через asyncio для скорости
   - Результат записать в payment_* поля каждого примера
   - Обработка ошибок: если Haiku не смог — оставить null

4. **Аугментация недопредставленных типов:**
   - Найти типы с <=5 примерами (50 из 74)
   - Для каждого: сгенерировать 3-5 дополнительных примеров через Haiku, попросив переформулировать существующие (варьировать контрагентов, даты, суммы, формулировки)
   - Формат — сразу tool call

5. **Edge cases (добавить к train):**
   - 10-15 negative examples: не-юридические тексты (письма, рецепты, статьи) → ответ `<tool_call>{"name": "extract_metadata", "arguments": {"document_type": "Нераспознанный документ", "counterparty": null, "subject": "Документ не является юридическим", ...все null/пустые...}}</tool_call>`
   - 10-15 edge cases OCR-мусор: текст с артефактами, битой кодировкой → аналогичный ответ
   - 10-15 нестандартных типов документов (модель должна создавать новые типы, а не только из списка)

6. **Сохранить результат:**
   - dataset/training/v2_train.jsonl
   - dataset/training/v2_val.jsonl
   - Вывести статистику: кол-во примеров, распределение типов, заполненность payment_*

Важно: НЕ использовать openai SDK. Использовать anthropic SDK напрямую для Haiku-субагента. Ключ из env ANTHROPIC_API_KEY.
  </action>
  <verify>
    <automated>cd /Users/danilakistenev/Downloads/Личное/ЮР\ тэг/yurteg && python3 -c "
import json
from pathlib import Path
train = [json.loads(l) for l in open('dataset/training/v2_train.jsonl')]
val = [json.loads(l) for l in open('dataset/training/v2_val.jsonl')]
# Check tool call format
sample = train[0]['messages'][-1]['content']
assert '<tool_call>' in sample and '</tool_call>' in sample, 'Missing tool_call tags'
# Check no confidence
parsed = json.loads(sample.replace('<tool_call>', '').replace('</tool_call>', ''))
args = parsed['arguments']
assert 'confidence' not in args, 'confidence not removed'
# Check payment_* fields exist
for f in ['payment_terms','payment_amount','payment_frequency','payment_direction']:
    assert f in args, f'Missing {f}'
# Check counts
print(f'Train: {len(train)}, Val: {len(val)}')
assert len(train) > 700, f'Too few train examples: {len(train)}'
assert len(val) > 80, f'Too few val examples: {len(val)}'
print('ALL CHECKS PASSED')
"</automated>
  </verify>
  <done>v2_train.jsonl и v2_val.jsonl в tool call формате, 13 полей, payment_* аннотированы, edge cases добавлены, >700 train примеров</done>
</task>

<task type="auto">
  <name>Task 2: Генерация DPO-пар и загрузка на HuggingFace</name>
  <files>dataset/v2_generate_dpo.py, dataset/v2_upload.py, dataset/sft_config.yaml, dataset/dpo_config.yaml</files>
  <action>
**A. dataset/v2_generate_dpo.py** — генерация 50-80 DPO-пар:

1. Загрузить v2_train.jsonl (результат Task 1)
2. Выбрать 75 разнообразных примеров (по типам документов)
3. Для каждого создать rejected-версию по одной из 5 категорий (по 15 пар):

   **Категория 1 — Невалидный JSON (15 пар):**
   - chosen: корректный `<tool_call>{"name": "extract_metadata", "arguments": {...}}</tool_call>`
   - rejected: тот же контент, но assistant отвечает plain text с ошибками JSON: unquoted keys, trailing commas, одинарные кавычки, missing brackets, текст до/после JSON
   - НЕ оборачивать в tool_call (модель не вызвала tool)

   **Категория 2 — Кривые даты (15 пар):**
   - chosen: даты YYYY-MM-DD
   - rejected: даты DD.MM.YYYY, "15 марта 2024", перепутаны date_signed и date_start, year-only "2024"

   **Категория 3 — Пустые массивы (15 пар):**
   - chosen: заполненные special_conditions и parties
   - rejected: special_conditions=[] и/или parties=[] когда данные есть в тексте

   **Категория 4 — Краткий subject (15 пар):**
   - chosen: развёрнутый subject ("Оказание юридических консультационных услуг по вопросам...")
   - rejected: generic subject ("Оказание услуг", "Поставка товара", "Подряд")

   **Категория 5 — Ошибки ФИО/падежей (15 пар):**
   - chosen: ФИО в именительном ("Иванов Иван Иванович")
   - rejected: ФИО в родительном/дательном ("Иванова Ивана Ивановича"), сокращения ("Иванов И.И.")

4. Формат каждой пары (совпадает с текущим dpo_claude_train.jsonl):
   ```json
   {
     "prompt": [system_msg, user_msg],
     "chosen": [assistant_msg_correct],
     "rejected": [assistant_msg_wrong]
   }
   ```

5. Разделить 90/10 → v2_dpo_train.jsonl + v2_dpo_val.jsonl
6. Сохранить в dataset/training/

**B. dataset/v2_upload.py** — загрузка на HF:

1. Загрузить файлы на SuperPuperD/yurteg-legal-sft:
   - v2_train.jsonl → train.jsonl (заменить)
   - v2_val.jsonl → val.jsonl (заменить)
   - v2_dpo_train.jsonl → dpo_train.jsonl (заменить dpo_claude_train.jsonl)
   - v2_dpo_val.jsonl → dpo_val.jsonl (заменить dpo_claude_val.jsonl)
   - Обновлённые sft_config.yaml и dpo_config.yaml
2. Использовать huggingface_hub.HfApi.upload_file()
3. Токен: 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
4. Commit message: "v2: tool call format, payment_* fields, 75 DPO pairs, edge cases"

**C. Обновить sft_config.yaml:**
- Комментарий обновить: "v2 — tool call format"
- val_set_size: 0 (у нас отдельный val.jsonl, не нужно split)
- Добавить val dataset section:
  ```yaml
  datasets:
    - path: SuperPuperD/yurteg-legal-sft
      type: chat_template
      chat_template: tokenizer_default
      field_messages: messages
      roles_to_train:
        - assistant
      data_files:
        - train.jsonl
  val_datasets:
    - path: SuperPuperD/yurteg-legal-sft
      type: chat_template
      chat_template: tokenizer_default
      field_messages: messages
      data_files:
        - val.jsonl
  ```

**D. Обновить dpo_config.yaml:**
- data_files: dpo_train.jsonl (вместо dpo_claude_train.jsonl)
- Комментарий: "75 DPO pairs, 5 error categories"
  </action>
  <verify>
    <automated>cd /Users/danilakistenev/Downloads/Личное/ЮР\ тэг/yurteg && python3 -c "
import json
from pathlib import Path
# Check DPO files
dpo_train = [json.loads(l) for l in open('dataset/training/v2_dpo_train.jsonl')]
dpo_val = [json.loads(l) for l in open('dataset/training/v2_dpo_val.jsonl')]
total = len(dpo_train) + len(dpo_val)
assert 50 <= total <= 80, f'DPO pairs out of range: {total}'
# Check DPO format
sample = dpo_train[0]
assert 'prompt' in sample and 'chosen' in sample and 'rejected' in sample, 'Wrong DPO format'
# Check chosen has tool_call
chosen_text = sample['chosen'][-1]['content'] if isinstance(sample['chosen'], list) else sample['chosen']
assert '<tool_call>' in str(chosen_text), 'Chosen missing tool_call'
print(f'DPO: {len(dpo_train)} train + {len(dpo_val)} val = {total} total')
print('ALL DPO CHECKS PASSED')
" && echo "---" && python3 -c "
import yaml
cfg = yaml.safe_load(open('dataset/sft_config.yaml'))
print('SFT config OK, val_set_size:', cfg.get('val_set_size'))
dpo = yaml.safe_load(open('dataset/dpo_config.yaml'))
print('DPO config OK, data_files:', dpo['datasets'][0].get('data_files'))
"</automated>
  </verify>
  <done>50-80 DPO-пар в 5 категориях, sft/dpo configs обновлены, все файлы загружены на HF</done>
</task>

</tasks>

<verification>
1. v2_train.jsonl: >700 примеров, все в `<tool_call>` формате, 13 полей, без confidence
2. v2_val.jsonl: >80 примеров, тот же формат
3. payment_* поля: аннотированы для договоров с платежами, null для остальных
4. DPO: 50-80 пар, 5 категорий, prompt/chosen/rejected формат
5. Edge cases: negative examples + OCR-мусор + нестандартные типы
6. HF: все файлы загружены в SuperPuperD/yurteg-legal-sft
7. Configs: sft_config.yaml и dpo_config.yaml обновлены для v2
</verification>

<success_criteria>
- `python3 dataset/v2_transform.py` выполняется без ошибок, создаёт v2_train/v2_val.jsonl
- `python3 dataset/v2_generate_dpo.py` создаёт 50-80 DPO-пар
- `python3 dataset/v2_upload.py` загружает всё на HF
- Формат каждого примера: messages с tool_call тегами в assistant content
- Схема: 13 полей (document_type...payment_direction), без confidence
</success_criteria>

<output>
After completion, create `.planning/quick/260320-vya-v2-tool-call-payment-dpo-edge-cases/260320-vya-SUMMARY.md`
</output>
