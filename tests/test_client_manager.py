"""Тесты мультиклиентского менеджера (Phase 3).

PROF-01: Один юрист ведёт несколько клиентов — изолированные реестры

Wave 0: тест-скелеты созданы до реализации (RED стадия).
Assertions дополняются после 03-05 (client_manager implementation).
"""
import pytest
from pathlib import Path


@pytest.fixture
def client_dir(tmp_path):
    """Создаёт временную директорию для хранения клиентских БД."""
    clients_dir = tmp_path / "clients"
    clients_dir.mkdir()
    return clients_dir


@pytest.mark.xfail(reason="PROF-01: ClientManager реализуется в 03-05", strict=False)
def test_add_client(client_dir):
    """PROF-01: add_client создаёт запись в clients.json с корректным путём к БД."""
    try:
        from services.client_manager import ClientManager
    except ImportError:
        pytest.xfail("services.client_manager не существует — реализуется в 03-05")

    manager = ClientManager(client_dir)
    manager.add_client("ООО Рога и Копыта")

    clients = manager.list_clients()
    assert "ООО Рога и Копыта" in clients, "Клиент должен появиться в списке после add_client"

    # Проверяем что db_path корректный
    db_path = manager.get_db_path("ООО Рога и Копыта")
    assert db_path is not None, "db_path не должен быть None"
    assert str(db_path).endswith(".db"), "db_path должен указывать на .db файл"


@pytest.mark.xfail(reason="PROF-01: ClientManager реализуется в 03-05", strict=False)
def test_get_db(client_dir):
    """PROF-01: get_db возвращает экземпляр Database с корректным путём."""
    try:
        from services.client_manager import ClientManager
        from modules.database import Database
    except ImportError:
        pytest.xfail("services.client_manager или modules.database не существует")

    manager = ClientManager(client_dir)
    manager.add_client("ИП Иванов")

    db = manager.get_db("ИП Иванов")
    assert isinstance(db, Database), f"get_db должен вернуть Database, получен {type(db)}"
    assert "ип_иванов" in str(db.db_path).lower() or "иванов" in str(db.db_path).lower(), (
        "Путь к БД должен содержать название клиента"
    )


@pytest.mark.xfail(reason="PROF-01: ClientManager реализуется в 03-05", strict=False)
def test_list_clients(client_dir):
    """PROF-01: list_clients возвращает всех добавленных клиентов."""
    try:
        from services.client_manager import ClientManager
    except ImportError:
        pytest.xfail("services.client_manager не существует — реализуется в 03-05")

    manager = ClientManager(client_dir)
    manager.add_client("Клиент А")
    manager.add_client("Клиент Б")
    manager.add_client("Клиент В")

    clients = manager.list_clients()
    assert "Клиент А" in clients
    assert "Клиент Б" in clients
    assert "Клиент В" in clients
    assert len(clients) >= 3, "Должны присутствовать все добавленные клиенты"


@pytest.mark.xfail(reason="PROF-01: ClientManager реализуется в 03-05", strict=False)
def test_default_client(client_dir):
    """PROF-01: 'Основной реестр' существует без вызовов add_client."""
    try:
        from services.client_manager import ClientManager
    except ImportError:
        pytest.xfail("services.client_manager не существует — реализуется в 03-05")

    manager = ClientManager(client_dir)  # Свежий менеджер без add_client

    clients = manager.list_clients()
    assert "Основной реестр" in clients, (
        "ClientManager должен автоматически создавать клиента 'Основной реестр'"
    )


@pytest.mark.xfail(reason="PROF-01: fuzzy matching реализуется в 03-05", strict=False)
def test_fuzzy_match_exact(client_dir):
    """PROF-01: find_client_by_counterparty находит точное совпадение по названию."""
    try:
        from services.client_manager import ClientManager
    except ImportError:
        pytest.xfail("services.client_manager не существует — реализуется в 03-05")

    manager = ClientManager(client_dir)
    manager.add_client("ООО Ромашка")

    result = manager.find_client_by_counterparty("ООО Ромашка")
    assert result == "ООО Ромашка", f"Точное совпадение должно найти клиента, получен {result}"


@pytest.mark.xfail(reason="PROF-01: fuzzy matching реализуется в 03-05", strict=False)
def test_fuzzy_match_reorder(client_dir):
    """PROF-01: 'Рога и Копыта ООО' совпадает с 'ООО Рога и Копыта' (fuzzy)."""
    try:
        from services.client_manager import ClientManager
    except ImportError:
        pytest.xfail("services.client_manager не существует — реализуется в 03-05")

    manager = ClientManager(client_dir)
    manager.add_client("ООО Рога и Копыта")

    result = manager.find_client_by_counterparty("Рога и Копыта ООО")
    assert result == "ООО Рога и Копыта", (
        f"Fuzzy matching должен найти 'ООО Рога и Копыта' по запросу 'Рога и Копыта ООО', получен {result}"
    )


@pytest.mark.xfail(reason="PROF-01: fuzzy matching реализуется в 03-05", strict=False)
def test_fuzzy_match_no_match(client_dir):
    """PROF-01: несвязанное название возвращает None."""
    try:
        from services.client_manager import ClientManager
    except ImportError:
        pytest.xfail("services.client_manager не существует — реализуется в 03-05")

    manager = ClientManager(client_dir)
    manager.add_client("ООО Ромашка")

    result = manager.find_client_by_counterparty("Совершенно Другая Компания ЗАО")
    assert result is None, (
        f"Несвязанное название должно возвращать None, получен {result}"
    )


@pytest.mark.xfail(reason="PROF-01: switch_client реализуется в 03-05", strict=False)
def test_switch_client(client_dir):
    """PROF-01: переключение клиента изменяет активный путь к БД."""
    try:
        from services.client_manager import ClientManager
    except ImportError:
        pytest.xfail("services.client_manager не существует — реализуется в 03-05")

    manager = ClientManager(client_dir)
    manager.add_client("Клиент X")
    manager.add_client("Клиент Y")

    manager.switch_client("Клиент X")
    active_x = manager.active_db_path

    manager.switch_client("Клиент Y")
    active_y = manager.active_db_path

    assert active_x != active_y, "После переключения клиента путь к БД должен измениться"
    assert "Клиент X" in str(active_x) or "клиент_x" in str(active_x).lower(), (
        "Путь при активном 'Клиент X' должен содержать его название"
    )
