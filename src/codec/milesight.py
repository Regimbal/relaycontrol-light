"""Codec for decoding Milesight SOS button payloads."""

import logging

def decode(payload: bytes) -> dict:
    """Decode a binary payload from a Milesight button."""
    battery_low = None
    alarm = None
    alarm_expire = None
    i = 0
    while i < len(payload):
        channel_id = payload[i]
        i += 1
        channel_type = payload[i]
        i += 1

        # BATTERY
        if channel_id == 0x01 and channel_type == 0x75:
            frame_type = "UP_HEARTBEAT"
            battery_low = payload[i] <= 50
            i += 1
        # PRESS STATE
        elif channel_id == 0xff and channel_type == 0x2e:
            frame_type = "UP_EVENT"
            type = payload[i]
            i += 1

            if type in {1, 2, 3}:
                alarm = True
                alarm_expire = True
            else:
                logging.warning("SOS: Unknown button action")
        else:
            break

    return {
        "applicationType": "SOS",
        "frameType": frame_type,
        "tamper": False,
        "battery_low": battery_low,
        "alarm": alarm,
        "alarm_expire": alarm_expire,
    }