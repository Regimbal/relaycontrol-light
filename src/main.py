import argparse
import logging
import threading
import sys, signal
from flask import Flask, jsonify, send_from_directory
from config_loader import load_config, get_log_level, get_dashboard_config
from logger_config import setup_logging
from mqtt_listener import start_mqtt, stop_mqtt
from state_manager import get_state

# MQTT thread
mqtt_thread = threading.Thread(target=start_mqtt, daemon=True)

app = Flask(__name__, static_folder="static")

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/state")
def api_state():
    return jsonify(get_state())


def graceful_exit():
    logging.info("Stopping program...")
    stop_mqtt()
    logging.info("Goodbye.")
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="Light relay controller")
    parser.add_argument("--config", help="Path to YAML configuration file")
    parser.add_argument("--log-level", help="Enforce devug level (DEBUG, INFO, WARNING, ERROR)")
    args = parser.parse_args()

    load_config(args.config)
    log_level = args.log_level or get_log_level()
    setup_logging(log_level)

    mqtt_thread.start()

    dashboard_cfg = get_dashboard_config()

    if dashboard_cfg.get("enable", False):
        app.run(host=dashboard_cfg.get("bind", "0.0.0.0"), port=dashboard_cfg.get("port", 8080))
    else:
        mqtt_thread.join()  # Keep running even without Flask
    

if __name__ == "__main__":
    signal.signal(signal.SIGINT, graceful_exit)
    signal.signal(signal.SIGTERM, graceful_exit)

    main()