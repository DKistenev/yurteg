<div align="center">

# ЮрТэг

**AI-помощник для работы с архивами договоров**

Десктопное приложение для автоматической обработки юридических документов. Загрузите папку с PDF и DOCX — получите структурированный реестр с метаданными за минуты, а не часы.

[Скачать DMG](https://github.com/DKistenev/yurteg/releases) | [Модель на HuggingFace](https://huggingface.co/SuperPuperD/yurteg-1.5b-v3-gguf)

</div>

---

## Что делает

ЮрТэг извлекает метаданные из договоров с помощью локальной AI-модели — без отправки данных в облако:

- **Тип документа** — из справочника 30+ типов (договор поставки, аренды, подряда...)
- **Контрагент, стороны** — с нормализацией ИП/ООО
- **Даты** — подписания, начала, окончания
- **Суммы и условия оплаты** — с определением периодичности и направления платежа
- **Особые условия** — штрафы, неустойки, гарантии

## Ключевые фичи

**Реестр договоров** — таблица с фильтрами, поиском, группировкой. Клик по строке открывает карточку документа с превью.

**Проверка по шаблону** — загрузите эталонный договор, система покажет все отклонения (redline). Скачивание DOCX с track changes для Word.

**Версии документов** — автоматическое связывание версий через embeddings. Сравнение с подсветкой изменений.

**Полностью локально** — AI-модель (QWEN 2.5 1.5B, ORPO fine-tune) и embedding-модель работают на устройстве. Данные не покидают компьютер.

## Стек

| Компонент | Технология |
|-----------|-----------|
| UI | NiceGUI + pywebview (native macOS) |
| AI-модель | QWEN 2.5 1.5B ORPO v3 via llama-server (llama.cpp) |
| Квантизация | GGUF Q4_K_M, 940 МБ |
| Embeddings | paraphrase-multilingual-MiniLM-L12-v2 (sentence-transformers) |
| БД | SQLite (per workspace) |
| Билд | PyInstaller → DMG (macOS ARM64) |
| CI/CD | GitHub Actions (tag v* → DMG) |

## Архитектура

```
Документ (PDF/DOCX)
    │
    ├── Scanner (извлечение текста)
    ├── Anonymizer (маскирование ПД)
    ├── AI Extractor (QWEN 1.5B + GBNF grammar → JSON)
    ├── Post-processor (fuzzy-match типов, нормализация, anti-hallucination)
    ├── Validator (confidence через logprobs)
    └── Database (SQLite + embeddings cache)
```

## Системные требования

| Параметр | Минимум |
|----------|---------|
| macOS | 13 Ventura+ |
| Процессор | Apple Silicon (M1/M2/M3/M4) |
| RAM | 4 ГБ |
| Диск | 3 ГБ свободных |
| Интернет | При первом запуске (~1.4 ГБ моделей) |

## Запуск из исходников

```bash
# Клонировать
git clone https://github.com/DKistenev/yurteg.git
cd yurteg

# Окружение
conda create -n yurteg python=3.12 -y
conda activate yurteg
pip install -r requirements.txt

# Запуск
PYTHONPATH="." python app/main.py
```

При первом запуске приложение скачает AI-модель (~940 МБ) и embedding-модель (~460 МБ).

## Сборка DMG

```bash
git tag v1.4.0
git push origin v1.4.0
```

GitHub Actions соберёт DMG автоматически (`.github/workflows/build-dmg.yml`).

## Модель

Fine-tuned QWEN 2.5 1.5B через ORPO (Odds Ratio Preference Optimization):
- **Датасет:** 1086 примеров, ручная разметка
- **Точность:** ~97% на тестовом наборе
- **GBNF grammar** для гарантированного JSON-вывода
- **Post-processing:** fuzzy-match типов, anti-hallucination проверка сумм

Модель: [SuperPuperD/yurteg-1.5b-v3-gguf](https://huggingface.co/SuperPuperD/yurteg-1.5b-v3-gguf)

## Лицензия

MIT
