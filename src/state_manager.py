# state_manager.py
import json, logging, yaml, time
import os
import threading
from datetime import datetime, timedelta
from sqlite_state_store import SQLiteStateStore
from sqlite_zone_store import SQLiteZoneStore
from relay_controller import send_tcp_command

STATE_FILE = "state.json"
DB_FILE = "state.db"

SAVE_INTERVAL_SECONDS = 3600  # toutes les heures

OFFLINE_THRESHOLD_HOURS = 24

class StateManager:
    def __init__(self, db_path=DB_FILE, json_path=STATE_FILE):
        self.store = SQLiteStateStore(db_path=db_path, json_path=json_path)
        self.zone_store = SQLiteZoneStore(db_path=db_path)
        self.state = self.store.load_all()
        self.zone_store = SQLiteZoneStore(db_path=db_path)
        self._reset_timers = {}
        self.zones = {}
        self.relay_state = {}
        self.lock = threading.Lock()
        self._start_offline_checker()

    
    def _start_offline_checker(self):
        def check_loop():
            while True:
                time.sleep(60)  # vérifie toutes les minutes
                with self.lock:
                    now = datetime.utcnow()
                    updated = False
                    for dev_eui, entry in self.state.items():
                        last_seen = entry.get("last_seen")
                        if not last_seen:
                            continue
                        try:
                            seen_time = datetime.fromisoformat(last_seen.rstrip("Z"))
                            offline = (now - seen_time) > timedelta(hours=OFFLINE_THRESHOLD_HOURS)
                            if entry.get("offline") != offline:
                                entry["offline"] = offline
                                updated = True
                        except Exception as e:
                            logging.warning(f"Could not parse last_seen for {dev_eui}: {e}")
                    if updated:
                        self._recompute_zones()
                        self._update_shared_relays()

        threading.Thread(target=check_loop, daemon=True).start()



    def update_sensor(self, dev_eui, dev_name, new_data: dict, touch_last_seen=True):
        with self.lock:
            if touch_last_seen:
                new_data["last_seen"] = datetime.utcnow().isoformat() + "Z"
                new_data["offline"] = False  # capteur vu = actif
            new_data["zone"] = dev_name.rsplit("_", 1)[-1] if dev_name and "_" in dev_name else None
            new_data["dev_name"] = dev_name
            old_zone = self.state.get(dev_eui, {}).get("zone")
            self.state[dev_eui] = new_data
            self.store.save_sensor(dev_eui, new_data)
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



    def _update_zone_status(self, zone):
        sensors = [c for c in self.state.values() if c.get("zone") == zone]
        prev = self.zones.get(zone, {})
        alarm = any(c.get("alarm") for c in sensors)
        tamper = any(c.get("tamper") for c in sensors)
        battery_low = any(c.get("battery_low") for c in sensors)
        offline = any(not c.get("offline") for c in sensors)
        self.zones[zone] = {
            "alarm": alarm,
            "tamper": tamper,
            "battery_low": battery_low,
            "offline": offline
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



    def _update_shared_relays(self):
        """Gère les relais partagés (hors 'alarm') : tamper, battery_low, offline."""
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
    
    def _apply_relay_state(self, ip, index, new_state):
        key = (ip, index)
        old_state = self.relay_state.get(key)
        if old_state != new_state:
            self.relay_state[key] = new_state
            send_tcp_command(ip, index, new_state)

    def _recompute_zones(self):
        for zone in self.zone_config:
            self._update_zone_status(zone)



    def get_state(self):
        with self.lock:
            return dict(self.state)

    def get_sensor(self, devEUI):
        with self.lock:
            return self.state.get(devEUI)

    def get_zone_states(self):
        return self.zones