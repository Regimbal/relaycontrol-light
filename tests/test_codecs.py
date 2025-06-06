import pytest
from codec import invissys, milesight


def test_invissys_he_event():
    payload = bytes([0x00, 0x4B, 0x01, 0x10, 0x00, 0x01])
    data = invissys.decode(payload)
    assert data == {
        "applicationType": "HE",
        "frameType": "UP_EVENT",
        "tamper": False,
        "battery_low": False,
        "alarm": True,
        "alarm_expire": False,
        "battery_voltage": 7.5,
    }


def test_invissys_opt_event():
    payload = bytes([0x01, 0x28, 0x10, 0x10, 0x00, 0x08])
    data = invissys.decode(payload)
    assert data == {
        "applicationType": "OPT",
        "frameType": "UP_EVENT",
        "tamper": True,
        "battery_low": False,
        "alarm": True,
        "alarm_expire": True,
        "battery_voltage": 4.0,
    }


def test_milesight_button_event():
    payload = bytes([0x01, 0x75, 40, 0xFF, 0x2E, 1])
    data = milesight.decode(payload)
    assert data == {
        "applicationType": "SOS",
        "frameType": "BUTTON",
        "tamper": False,
        "battery_low": True,
        "alarm": True,
        "alarm_expire": True,
    }