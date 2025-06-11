import logging
import pytest
import time

import state_manager as sm
from sqlite_zone_store import SQLiteZoneStore
import tempfile


def setup_manager(monkeypatch):
    monkeypatch.setattr(sm.StateManager, "_start_offline_checker", lambda self: None)
    monkeypatch.setattr(SQLiteZoneStore, "migrate_from_yaml", lambda self: None)

    zone_cfg = {
        "Z1": {"ip": "127.0.0.1", "alarm": 1, "tamper": 2, "battery_low": 3, "offline": 4},
        "Z2": {"ip": "127.0.0.1", "alarm": 5, "tamper": 2, "battery_low": 3, "offline": 4},
    }
    monkeypatch.setattr(SQLiteZoneStore, "load_all", lambda self: zone_cfg)

    commands = []
    def fake_send(ip, index, state):
        commands.append((ip, index, state))
    monkeypatch.setattr(sm, "send_tcp_command", fake_send)

    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    manager = sm.StateManager(db_path=tmp.name, json_path=None)
    return manager, commands


def test_zone_update(monkeypatch):
    manager, commands = setup_manager(monkeypatch)

    manager.update_sensor("A", "sensor1_Z1", {"alarm": True, "tamper": True})
    assert manager.zones["Z1"]["alarm"] is True
    assert manager.zones["Z1"]["tamper"] is True
    assert manager.zones["Z1"]["battery_low"] is False
    assert manager.zones["Z1"]["offline"] is False
    assert len(commands) == 4
    assert ("127.0.0.1", 1, True) in commands
    assert ("127.0.0.1", 2, True) in commands
    assert ("127.0.0.1", 3, False) in commands
    assert ("127.0.0.1", 4, False) in commands

    commands.clear()
    manager.update_sensor("B", "sensor2_Z1", {"battery_low": True})
    assert manager.zones["Z1"]["battery_low"] is True
    assert len(commands) == 1
    assert ("127.0.0.1", 3, True) in commands

    commands.clear()
    manager.update_sensor("C", "sensor3_Z2", {"battery_low": True})
    assert manager.zones["Z2"]["battery_low"] is True
    assert len(commands) == 1
    assert ("127.0.0.1", 5, False) in commands

    commands.clear()
    manager.update_sensor("B", "sensor2_Z1", {"battery_low": False})
    assert manager.zones["Z1"]["battery_low"] is False
    assert len(commands) == 0

    commands.clear()
    manager.update_sensor("C", "sensor3_Z2", {"battery_low": False})
    assert manager.zones["Z2"]["battery_low"] is False
    assert len(commands) == 1
    assert ("127.0.0.1", 3, False) in commands


def test_offline_detection(monkeypatch):
    manager, commands = setup_manager(monkeypatch)
    monkeypatch.setattr(sm, "OFFLINE_THRESHOLD_HOURS", 0)

    manager.update_sensor("X", "sensor_Z1", {"alarm": False})
    commands.clear()
    manager.state["X"]["last_seen"] = "2000-01-01T00:00:00"

    manager.run_offline_check()

    assert manager.state["X"]["offline"] is True
    assert manager.zones["Z1"]["offline"] is True
    assert len(commands) == 1
    assert ("127.0.0.1", 4, True) in commands


class FakeTimer:
    def __init__(self, interval, func):
        self.func = func

    def start(self):
        sm.threading.Thread(target=self.func).start()

    def cancel(self):
        pass


def test_alarm_auto_reset(monkeypatch):
    manager, commands = setup_manager(monkeypatch)
    monkeypatch.setattr(sm.threading, "Timer", FakeTimer)

    manager.update_sensor("A1", "sensor_Z1", {"alarm": True, "alarm_expire": True})
    time.sleep(0.05)

    assert manager.zones["Z1"]["alarm"] is False
    assert ("127.0.0.1", 1, True) in commands
    assert ("127.0.0.1", 1, False) in commands