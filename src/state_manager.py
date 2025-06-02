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
        self.relay_state = {}
        self.lock = threading.Lock()
        self.dobackup = False
        self._start_auto_save()

        #with open("config/zones.yaml") as f:
        #    self.zone_config = yaml.safe_load(f)

    def _apply_relay_state(self, ip, index, new_state):
        key = (ip, index)
        old_state = self.relay_state.get(key)
        if old_state != new_state:
            self.relay_state[key] = new_state
            send_tcp_command(ip, index, new_state)

    def _update_shared_relays(self):
        """Gère les relais partagés (hors 'alarm') : tamper, battery_low, online."""
        relay_groups = {}

        for zone, config in self.zone_config.items():
            ip = config.get("ip")
            for field, relay_index in config.items():
                if field in ["ip", "alarm"]:
                    continue
                if relay_index is None:
                    continue
                key = (ip, relay_index)
                if key not in relay_groups:
                    relay_groups[key] = {"field": field, "zones": []}
                relay_groups[key]["zones"].append(zone)

        for (ip, relay_index), group in relay_groups.items():
            field = group["field"]
            zones = group["zones"]

            # Le relais doit être ON si au moins une zone a le champ concerné à True
            active = any(self.zones.get(z, {}).get(field, False) for z in zones)
            self._apply_relay_state(ip, relay_index, active)

    def _update_zone_status(self, zone):
        sensors = [c for c in self.state.values() if c.get("zone") == zone]
        prev = self.zones.get(zone, {})
        alarm = any(c.get("alarm") for c in sensors)
        tamper = any(c.get("tamper") for c in sensors)
        battery_low = any(c.get("battery_low") for c in sensors)
        offline = any(not c.get("online", True) for c in sensors)
        self.zones[zone] = {
            "alarm": alarm,
            "tamper": tamper,
            "battery_low": battery_low,
            "online": not offline
        }
        logging.info(f"Updates zones: {self.zones}")
        config = self.zone_config.get(zone)
        if not config:
            logging.warning("no config file for zones found")
            return

        # Commande pour le champ non partagé 'alarm'
        if "alarm" in config and prev.get("alarm") != alarm:
            self._apply_relay_state(config["ip"], config["alarm"], alarm)

        # MàJ des relais partagés
        self._update_shared_relays()

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