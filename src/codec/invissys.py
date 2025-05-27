import logging

applicationTypeMap = {
    1: "HE",
    2: "DIFENCE",
    16: "OPT"
}

frameIdMap = {
    0: "UP_HEARTBEAT",
    1: "UP_ID",
    2: "UP_CONFIG",
    16: "UP_EVENT",
    255: "UP_STATS"
}

def decode(payload: bytes) -> dict:
    if len(payload) < 4:
        raise ValueError("Payload too short")

    application_type = applicationTypeMap.get(payload[2], "UNKNOWN")
    frame_type = frameIdMap.get(payload[3], "UNKNOWN")

    tamper = None
    battery_low = False
    power_supply = None
    alarm = None
    alarm_expire = False

    if application_type == "HE":
        power_supply = (payload[1] & 0x7F) / 10
        battery_low = power_supply <= 3.3
        tamper = False
    elif application_type == "OPT":
        power_supply = (payload[1] & 0x7F) / 10
        battery_low = power_supply <= 2.5
        tamper = bool(payload[0] & 0x01)
    else:
        logging.warning("Unknown application type")

    if frame_type == "UP_EVENT":
        if application_type == "HE":
            if len(payload) < 6:
                raise ValueError("Payload too short for UP_EVENT frame (need at least 6 bytes)")
            alarm = bool(payload[5] & 0x01)
        elif application_type == "OPT":
            if len(payload) < 6:
                raise ValueError("Payload too short for UP_EVENT frame (need at least 6 bytes)")
            infrared_trouble = bool((payload[5] >> 4) & 0x01)
            infrared_detect4 = bool((payload[5] >> 3) & 0x01)
            infrared_detect3 = bool((payload[5] >> 2) & 0x01)
            infrared_detect2 = bool((payload[5] >> 1) & 0x01)
            infrared_detect1 = bool(payload[5] & 0x01)
            alarm = infrared_trouble or infrared_detect1 or infrared_detect2 or infrared_detect3 or infrared_detect4
            alarm_expire = True
        else:
            logging.warning("No alarm matching field")
    else:
        logging.warning("Not an event")

    return {
        "applicationType": application_type,
        "frameType": frame_type,
        "tamper": tamper,
        "battery_low": battery_low,
        "alarm": alarm,
        "alarm_expire": alarm_expire,
        "battery_voltage": power_supply,
    }
