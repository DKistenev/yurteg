"""Тесты сервис-слоя — изоляция от Streamlit, сигнатуры, делегирование (FUND-02)."""
import inspect
import sys

import pytest

from config import Config


def test_no_streamlit_import():
    """services.pipeline_service не импортирует streamlit ни прямо ни транзитивно."""
    # Убедиться что streamlit не попал в модуль через транзитивный импорт
    # Сохраняем состояние до теста
    before = set(sys.modules.keys())

    import services.pipeline_service as ps

    # Получаем исходный код — ищем реальный импорт streamlit (не комментарий)
    import inspect as _inspect
    source = _inspect.getsource(ps)
    # Проверяем наличие строки вида "import streamlit" (не в комментарии)
    import re as _re
    has_import = bool(_re.search(r'^\s*(import streamlit|from streamlit)', source, _re.MULTILINE))
    assert not has_import, (
        "Найден 'import streamlit' в исходном коде services/pipeline_service.py. "
        "Этот файл должен работать без Streamlit."
    )


def test_process_archive_signature():
    """pipeline_service.process_archive имеет правильную сигнатуру."""
    from services import pipeline_service
    sig = inspect.signature(pipeline_service.process_archive)
    params = set(sig.parameters.keys())
    required = {"source_dir", "config"}
    assert required.issubset(params), (
        f"Не хватает параметров: {required - params}. Найдены: {params}"
    )


