import pytest
from codec import invissys, milesight

# Test HE HEARTBEAT mais bat faible
def test_invissys_he_heartbeat_lowbat():
    payload = bytes([0x00, 0x21, 0x01, 0x00, 0x00])
    data = invissys.decode(payload)
    assert data == {
        "applicationType": "HE",
        "frameType": "UP_HEARTBEAT",
        "tamper": False,
        "battery_low": True,
        "alarm": None,
        "alarm_expire": None,
        "battery_voltage": 3.3,
    }

# Test HE EVENT ouvert
def test_invissys_he_event_open():
    payload = bytes([0x00, 0x23, 0x01, 0x10, 0x10, 0x01])
    data = invissys.decode(payload)
    assert data == {
        "applicationType": "HE",
        "frameType": "UP_EVENT",
        "tamper": False,
        "battery_low": False,
        "alarm": True,
        "alarm_expire": False,
        "battery_voltage": 3.5,
    }

# Test HE EVENT ferme
def test_invissys_he_event_close():
    payload = bytes([0x00, 0x23, 0x01, 0x10, 0x10, 0x00])
    data = invissys.decode(payload)
    assert data == {
        "applicationType": "HE",
        "frameType": "UP_EVENT",
        "tamper": False,
        "battery_low": False,
        "alarm": False,
        "alarm_expire": False,
        "battery_voltage": 3.5,
    }

def test_invissys_opt_heartbeat():
    payload = bytes([0x00, 0x20, 0x10, 0x00])
    data = invissys.decode(payload)
    assert data == {
        "applicationType": "OPT",
        "frameType": "UP_HEARTBEAT",
        "tamper": False,
        "battery_low": False,
        "alarm": None,
        "alarm_expire": None,
        "battery_voltage": 3.2,
    }

def test_invissys_opt_heartbeat_tamper_lowbat():
    payload = bytes([0x01, 0x19, 0x10, 0x00])
    data = invissys.decode(payload)
    assert data == {
        "applicationType": "OPT",
        "frameType": "UP_HEARTBEAT",
        "tamper": True,
        "battery_low": True,
        "alarm": None,
        "alarm_expire": None,
        "battery_voltage": 2.5,
    }

def test_invissys_opt_event():
    payload = bytes([0x00, 0x1E, 0x10, 0x10, 0x01, 0x08])
    data = invissys.decode(payload)
    assert data == {
        "applicationType": "OPT",
        "frameType": "UP_EVENT",
        "tamper": False,
        "battery_low": False,
        "alarm": True,
        "alarm_expire": True,
        "battery_voltage": 3.0,
    }

def test_invissys_opt_event_tamper():
    payload = bytes([0x01, 0x1E, 0x10, 0x10, 0x01, 0x01])
    data = invissys.decode(payload)
    assert data == {
        "applicationType": "OPT",
        "frameType": "UP_EVENT",
        "tamper": True,
        "battery_low": False,
        "alarm": True,
        "alarm_expire": True,
        "battery_voltage": 3.0,
    }


def test_milesight_button_heartbeat():
    payload = bytes([0x01, 0x75, 0x64])
    data = milesight.decode(payload)
    assert data == {
        "applicationType": "SOS",
        "frameType": "UP_HEARTBEAT",
        "tamper": False,
        "battery_low": False,
        "alarm": None,
        "alarm_expire": None,
    }

def test_milesight_button_heartbeat_lowbat():
    payload = bytes([0x01, 0x75, 0x32])
    data = milesight.decode(payload)
    assert data == {
        "applicationType": "SOS",
        "frameType": "UP_HEARTBEAT",
        "tamper": False,
        "battery_low": True,
        "alarm": None,
        "alarm_expire": None,
    }

def test_milesight_button_event():
    payload = bytes([0xff, 0x2e, 0x03])
    data = milesight.decode(payload)
    assert data == {
        "applicationType": "SOS",
        "frameType": "UP_EVENT",
        "tamper": False,
        "battery_low": None,
        "alarm": True,
        "alarm_expire": True,
    }