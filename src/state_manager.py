# state_manager.py
import json
import os
from datetime import datetime

STATE_FILE = "state.json"

class StateManager:
    def __init__(self, filename=STATE_FILE):
        self.filename = filename
        self.state = self._load_state()

    def _load_state(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load state file: {e}")
        return {}

    def _save_state(self):
        try:
            with open(self.filename, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state file: {e}")

    def update_sensor(self, dev_eui, dev_name, new_data: dict):
        new_data["last_seen"] = datetime.utcnow().isoformat() + "Z"
        new_data["zone"] = dev_name.rsplit("_", 1)[-1] if dev_name and "_" in dev_name else None
        self.state[dev_eui] = new_data
        self._save_state()

    def get_state(self):
        return self.state

    def get_sensor(self, devEUI):
        return self.state.get(devEUI)
