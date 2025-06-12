import yaml
import os
import copy

DEFAULT_CONFIG = {
    "log": {
        "level": "WARNING"
    },
    "mqtt": {
        "broker": "localhost",
        "port": 1883,
        "topic": "application/+/device/+/event/up",
        "use_tls": False,
        "ca_cert": "",
        "tls_cert": "",
        "tls_key": "",
        "username": "",
        "password": ""
    },
    "dashboard": {
        "enable": True,
        "bind": "0.0.0.0",
        "port": 8080
    }
    
}

CONFIG = copy.deepcopy(DEFAULT_CONFIG)

def load_config(path=None):
    global CONFIG
    if path and os.path.exists(path):
        try:
            with open(path, "r") as f:
                user_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML configuration file {path}: {e}")
            return

        if user_config is None:
            return

        if not isinstance(user_config, dict):
            print(f"Configuration in {path} is not a dictionary, ignoring")
            return

        merge_dict(CONFIG, user_config)


def merge_dict(base, updates):
    for k, v in updates.items():
        if isinstance(v, dict) and k in base:
            merge_dict(base[k], v)
        else:
            base[k] = v

def get_log_level():
    return CONFIG.get("log", {}).get("level", "INFO")

def get_mqtt_config():
    return CONFIG["mqtt"]

def get_dashboard_config():
    return CONFIG["dashboard"]
