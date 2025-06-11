import base64
import json
import sys
import types

# Provide a minimal stub for the paho.mqtt.client module used by mqtt_listener
mqtt_stub = types.SimpleNamespace(Client=lambda client_id=None: types.SimpleNamespace())
sys.modules.setdefault("paho", types.SimpleNamespace(mqtt=types.SimpleNamespace(client=mqtt_stub)))
sys.modules.setdefault("paho.mqtt", types.SimpleNamespace(client=mqtt_stub))
sys.modules.setdefault("paho.mqtt.client", mqtt_stub)

import mqtt_listener

class DummyStateManager:
    def __init__(self):
        self.calls = []

    def update_sensor(self, dev_eui, dev_name, data):
        self.calls.append((dev_eui, dev_name, data))

class DummyMsg:
    def __init__(self, payload):
        self.payload = payload


def run_on_message(payload_dict, monkeypatch):
    dummy = DummyStateManager()
    monkeypatch.setattr(mqtt_listener, "state_manager", dummy)
    msg = DummyMsg(json.dumps(payload_dict).encode())
    mqtt_listener.on_message(None, None, msg)
    return dummy.calls


def test_on_message_hex(monkeypatch):
    payload_hex = "0021010000"
    expected = {
        "applicationType": "HE",
        "frameType": "UP_HEARTBEAT",
        "tamper": False,
        "battery_low": True,
        "alarm": None,
        "alarm_expire": None,
        "battery_voltage": 3.3,
    }
    payload = {
        "devEUI": "A",
        "deviceName": "sensor",
        "applicationName": "invissys",
        "data_encode": "hexstring",
        "data": payload_hex,
    }
    calls = run_on_message(payload, monkeypatch)
    assert calls == [("A", "sensor", expected)]


def test_on_message_base64(monkeypatch):
    payload_bytes = bytes.fromhex("0021010000")
    payload_base64 = base64.b64encode(payload_bytes).decode()
    expected = {
        "applicationType": "HE",
        "frameType": "UP_HEARTBEAT",
        "tamper": False,
        "battery_low": True,
        "alarm": None,
        "alarm_expire": None,
        "battery_voltage": 3.3,
    }
    payload = {
        "devEUI": "B",
        "deviceName": "sensor",
        "applicationName": "invissys",
        "data_encode": "base64",
        "data": payload_base64,
    }
    calls = run_on_message(payload, monkeypatch)
    assert calls == [("B", "sensor", expected)]