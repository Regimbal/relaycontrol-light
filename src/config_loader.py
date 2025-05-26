import yaml
import os

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

CONFIG = DEFAULT_CONFIG.copy()

def load_config(path=None):
    global CONFIG
    if path and os.path.exists(path):
        with open(path, "r") as f:
            user_config = yaml.safe_load(f)
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
