# state_manager.py
import json, logging, yaml
import os
import threading
from datetime import datetime, timedelta
from relay_controller import send_tcp_command

STATE_FILE = "state.json"

OFFLINE_THRESHOLD_HOURS = 24

class StateManager:
    def __init__(self, filename=STATE_FILE):
        self.filename = filename
        self.state = self._load_state()
        self._reset_timers = {}
        self.zones = {}
        with open("config/zones.yaml") as f:
            self.zone_config = yaml.safe_load(f)

    def _update_zone_status(self, zone):
        sensors = [c for c in self.state.values() if c.get("zone") == zone]
        alarm = any(c.get("alarm") for c in sensors)
        tamper = any(c.get("tamper") for c in sensors)
        prev = self.zones.get(zone, {})
        self.zones[zone] = {"alarm": alarm, "tamper": tamper}
        logging.info(f"Updates zones: {self.zones}")
        config = self.zone_config.get(zone)
        if not config:
            logging.warning("no config file for zones found")
            return
        # Comparaison et envoi des commandes TCP
        for key in ["alarm", "tamper"]:
            if key not in config:
                continue
            if prev.get(key) != self.zones[zone][key]:
                relay_index = config[key]
                ip = config["ip"]
                send_tcp_command(ip, relay_index, self.zones[zone][key])


    def _load_state(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r") as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Could not load state file: {e}")
        return {}

    def _save_state(self):
        try:
            with open(self.filename, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logging.warning(f"Could not save state file: {e}")

    def update_sensor(self, dev_eui, dev_name, new_data: dict, touch_last_seen=True):
        if touch_last_seen:
            new_data["last_seen"] = datetime.utcnow().isoformat() + "Z"
        new_data["zone"] = dev_name.rsplit("_", 1)[-1] if dev_name and "_" in dev_name else None
        new_data["dev_name"] = dev_name
        self.state[dev_eui] = new_data
        self._save_state()
        logging.debug(f"Updated state for {dev_eui}: {new_data}")
        if new_data.get("zone"):
            self._update_zone_status(new_data["zone"])
        if new_data.get("alarm") and new_data.get("alarm_expire"):
            self._schedule_alarm_reset(dev_eui, dev_name)

    def _schedule_alarm_reset(self, dev_eui, dev_name):
        def reset():
            entry = self.state.get(dev_eui)
            if entry and entry.get("alarm"):
                logging.debug(f"Alarm reset for {dev_eui}")
                entry["alarm"] = False
                self.update_sensor(dev_eui, dev_name, entry, touch_last_seen=False)
            self._reset_timers.pop(dev_eui, None)

        if dev_eui in self._reset_timers:
            self._reset_timers[dev_eui].cancel()

        timer = threading.Timer(5.0, reset)
        timer.daemon = True
        self._reset_timers[dev_eui] = timer
        timer.start()

    def get_state(self):
        now = datetime.utcnow()
        result = {}
        for dev_eui, entry in self.state.items():
            last_seen = entry.get("last_seen")
            online = False
            if last_seen:
                try:
                    seen_time = datetime.fromisoformat(last_seen.rstrip("Z"))
                    online = (now - seen_time) < timedelta(hours=OFFLINE_THRESHOLD_HOURS)
                except Exception as e:
                    logging.error(f"Failed parsing last_seen {dev_eui}: {e}")
            result[dev_eui] = {**entry, "online": online}
        return result

    def get_sensor(self, devEUI):
        return self.state.get(devEUI)

    def get_zone_states(self):
        return self.zones