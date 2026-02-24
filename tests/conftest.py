"""Конфигурация pytest — добавляет корень проекта в sys.path."""
import sys
from pathlib import Path

# Добавляем yurteg/ в sys.path чтобы import config, modules.* работали
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
