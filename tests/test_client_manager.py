"""Тесты мультиклиентского менеджера (Phase 3).

PROF-01: Один юрист ведёт несколько клиентов — изолированные реестры

Реализовано в 03-05: services/client_manager.py.
"""
import pytest
from pathlib import Path


@pytest.fixture
def client_dir(tmp_path):
    """Создаёт временную директорию для хранения клиентских БД."""
    clients_dir = tmp_path / "clients"
    clients_dir.mkdir()
    return clients_dir


def test_add_client(client_dir):
    """PROF-01: add_client создаёт запись в clients.json с корректным путём к БД."""
    from services.client_manager import ClientManager

    manager = ClientManager(client_dir)
    manager.add_client("ООО Рога и Копыта")

    clients = manager.list_clients()
    assert "ООО Рога и Копыта" in clients, "Клиент должен появиться в списке после add_client"

    db_path = manager.get_db_path("ООО Рога и Копыта")
    assert db_path is not None, "db_path не должен быть None"
    assert str(db_path).endswith(".db"), "db_path должен указывать на .db файл"
    assert "client_" in str(db_path), "db_path должен содержать префикс 'client_'"


def test_get_db(client_dir):
    """PROF-01: get_db возвращает экземпляр Database с корректным путём."""
    from services.client_manager import ClientManager
    from modules.database import Database

    manager = ClientManager(client_dir)
    manager.add_client("ИП Иванов")

    db = manager.get_db("ИП Иванов")
    assert isinstance(db, Database), f"get_db должен вернуть Database, получен {type(db)}"
    assert "иванов" in str(db.db_path).lower() or "ип_иванов" in str(db.db_path).lower(), (
        "Путь к БД должен содержать название клиента"
    )


def test_list_clients(client_dir):
    """PROF-01: list_clients возвращает всех добавленных клиентов."""
    from services.client_manager import ClientManager

    manager = ClientManager(client_dir)
    manager.add_client("Клиент А")
    manager.add_client("Клиент Б")
    manager.add_client("Клиент В")

    clients = manager.list_clients()
    assert "Клиент А" in clients
    assert "Клиент Б" in clients
    assert "Клиент В" in clients
    assert len(clients) >= 3, "Должны присутствовать все добавленные клиенты"


def test_default_client(client_dir):
    """PROF-01: 'Основной реестр' существует без вызовов add_client."""
    from services.client_manager import ClientManager

    manager = ClientManager(client_dir)

    clients = manager.list_clients()
    assert "Основной реестр" in clients, (
        "ClientManager должен автоматически создавать клиента 'Основной реестр'"
    )


def test_fuzzy_match_exact(client_dir):
    """PROF-01: find_client_by_counterparty находит точное совпадение по названию."""
    from services.client_manager import ClientManager

    manager = ClientManager(client_dir)
    manager.add_client("ООО Ромашка")

    result = manager.find_client_by_counterparty("ООО Ромашка")
    assert result == "ООО Ромашка", f"Точное совпадение должно найти клиента, получен {result}"


def test_fuzzy_match_reorder(client_dir):
    """PROF-01: 'Рога и Копыта ООО' совпадает с 'ООО Рога и Копыта' (fuzzy)."""
    from services.client_manager import ClientManager

    manager = ClientManager(client_dir)
    manager.add_client("ООО Рога и Копыта")

    result = manager.find_client_by_counterparty("Рога и Копыта ООО")
    assert result == "ООО Рога и Копыта", (
        f"Fuzzy matching должен найти 'ООО Рога и Копыта' по запросу 'Рога и Копыта ООО', получен {result}"
    )


def test_fuzzy_match_no_match(client_dir):
    """PROF-01: несвязанное название возвращает None."""
    from services.client_manager import ClientManager

    manager = ClientManager(client_dir)
    manager.add_client("ООО Ромашка")

    result = manager.find_client_by_counterparty("Совершенно Другая Компания ЗАО")
    assert result is None, (
        f"Несвязанное название должно возвращать None, получен {result}"
    )


def test_switch_client(client_dir):
    """PROF-01: get_db для разных клиентов возвращает разные db_path."""
    from services.client_manager import ClientManager

    manager = ClientManager(client_dir)
    manager.add_client("Клиент X")
    manager.add_client("Клиент Y")

    db_x = manager.get_db("Клиент X")
    db_y = manager.get_db("Клиент Y")

    assert db_x.db_path != db_y.db_path, (
        "get_db для разных клиентов должен возвращать разные db_path"
    )
    assert "клиент_x" in str(db_x.db_path).lower() or "client_" in str(db_x.db_path).lower(), (
        "Путь к БД клиента X должен отличаться от клиента Y"
    )


def test_get_db_reuses_cached_connection(client_dir):
    """Повторный get_db для одного пути должен возвращать тот же Database."""
    from services.client_manager import ClientManager

    manager = ClientManager(client_dir)
    manager.add_client("Клиент Cache")

    db1 = manager.get_db("Клиент Cache")
    db2 = manager.get_db("Клиент Cache")

    assert db1 is db2


def test_close_all_clears_cached_connections(client_dir):
    """close_all должен сбрасывать кэш соединений между тестами/сессиями."""
    from services.client_manager import ClientManager

    manager = ClientManager(client_dir)
    manager.add_client("Клиент Cleanup")

    db1 = manager.get_db("Клиент Cleanup")
    ClientManager.close_all()
    db2 = manager.get_db("Клиент Cleanup")

    assert db1 is not db2
