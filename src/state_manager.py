# state_manager.py
import json, logging, yaml, time
import os
import threading
from datetime import datetime, timedelta
from relay_controller import send_tcp_command

STATE_FILE = "state.json"
SAVE_INTERVAL_SECONDS = 60  # toutes les heures

OFFLINE_THRESHOLD_HOURS = 24

class StateManager:
    def __init__(self, filename=STATE_FILE):
        self.filename = filename
        self.state = self._load_state()
        self._reset_timers = {}
        self.zones = {}
        self.zone_config = {}
        self.aggregate_config = {}
        self.lock = threading.Lock()
        self.dobackup = False
        self._start_auto_save()

        zones_raw = yaml.safe_load(open("config/zones.yaml"))

        for key, val in zones_raw.items():
            if key == "__aggregates__":
                self.aggregate_config = val
            else:
                self.zone_config[key] = val

    def update_aggregate_relays(self):
        if not self.aggregate_config:
            return

        # Batterie faible : au moins un capteur concerné
        if "battery_low" in self.aggregate_config:
            battery_low = any(sensor.get("battery_low") for sensor in self.state.values())
            cfg = self.aggregate_config["battery_low"]
            send_tcp_command(cfg["ip"], cfg["relay"], battery_low)

        # Connectivité : au moins un capteur offline
        if "connectivity" in self.aggregate_config:
            any_offline = any(not sensor.get("online", False) for sensor in self.state.values())
            cfg = self.aggregate_config["connectivity"]
            send_tcp_command(cfg["ip"], cfg["relay"], any_offline)

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
    
    def _atomic_save(self):
        tmp_file = self.filename + ".tmp"
        try:
            with open(tmp_file, "w") as f:
                json.dump(self.state, f, indent=2)
            os.replace(tmp_file, self.filename)
        except Exception as e:
            logging.error(f"Could not save state file: {e}")
        
    def _start_auto_save(self):
        def save_loop():
            while True:
                time.sleep(SAVE_INTERVAL_SECONDS)
                with self.lock:
                    if self.dobackup:
                        self._atomic_save()
                        self.dobackup = False
                        logging.info(f"State saved to {self.filename} at {datetime.utcnow().isoformat()}Z")
                    else:
                        logging.debug("No change in state — skipping save.")
        thread = threading.Thread(target=save_loop, daemon=True).start()

    def update_sensor(self, dev_eui, dev_name, new_data: dict, touch_last_seen=True):
        with self.lock:
            if touch_last_seen:
                new_data["last_seen"] = datetime.utcnow().isoformat() + "Z"
            new_data["zone"] = dev_name.rsplit("_", 1)[-1] if dev_name and "_" in dev_name else None
            new_data["dev_name"] = dev_name
            old_zone = self.state.get(dev_eui, {}).get("zone")
            self.state[dev_eui] = new_data
            self.dobackup = True
            logging.debug(f"Updated state for {dev_eui}: {new_data}")
            if old_zone and old_zone != new_data.get("zone"):
                self._update_zone_status(old_zone)
            if new_data.get("zone"):
                self._update_zone_status(new_data["zone"])
            if new_data.get("alarm") and new_data.get("alarm_expire"):
                self._schedule_alarm_reset(dev_eui, dev_name)
            self.update_aggregate_relays()

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
        with self.lock:
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
        with self.lock:
            return self.state.get(devEUI)

    def get_zone_states(self):
        return self.zones