import logging
import pytest

import state_manager as sm
from sqlite_zone_store import SQLiteZoneStore
import tempfile


def setup_manager(monkeypatch):
    monkeypatch.setattr(sm.StateManager, "_start_offline_checker", lambda self: None)
    monkeypatch.setattr(SQLiteZoneStore, "migrate_from_yaml", lambda self: None)

    commands = []
    def fake_send(ip, index, state):
        commands.append((ip, index, state))
    monkeypatch.setattr(sm, "send_tcp_command", fake_send)

    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    manager = sm.StateManager(db_path=tmp.name, json_path=None)
    manager.zone_config = {
        "Z1": {"ip": "127.0.0.1", "alarm": 1, "tamper": 2, "battery_low": 3, "offline": 4},
        "Z2": {"ip": "127.0.0.1", "alarm": 5, "tamper": 2, "battery_low": 3, "offline": 4},
    }
    return manager, commands


def test_zone_update(monkeypatch):
    manager, commands = setup_manager(monkeypatch)

    manager.update_sensor("A", "sensor1_Z1", {"alarm": True})
    assert manager.zones["Z1"]["alarm"] is True
    assert ("127.0.0.1", 1, True) in commands

    manager.update_sensor("B", "sensor2_Z1", {"battery_low": True})
    assert manager.zones["Z1"]["battery_low"] is True
    assert ("127.0.0.1", 3, True) in commands

    commands.clear()
    manager.update_sensor("B", "sensor2_Z1", {"battery_low": False})
    assert manager.zones["Z1"]["battery_low"] is False
    assert ("127.0.0.1", 3, False) in commands

    commands.clear()
    manager.update_sensor("C", "sensor3_Z2", {"battery_low": True})
    assert manager.zones["Z2"]["battery_low"] is True
    assert ("127.0.0.1", 3, True) in commands

    commands.clear()
    manager.update_sensor("C", "sensor3_Z2", {"battery_low": False})
    assert manager.zones["Z2"]["battery_low"] is False
    assert ("127.0.0.1", 3, False) in commands