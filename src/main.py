"""Application entry point and HTTP API for relay control."""

import argparse
import logging
import threading
import sys
import signal
from flask import Flask, jsonify, send_from_directory, request, abort
from config_loader import (
    load_config,
    get_log_level,
    get_dashboard_config,
    get_mqtt_config,
)
from logger_config import setup_logging
from mqtt_listener import start_mqtt, stop_mqtt
from state_manager import StateManager
from state_manager_instance import state_manager

# MQTT thread placeholder, created in main()
mqtt_thread = None

def create_app() -> Flask:
    """Create the Flask application with all routes registered."""

    app = Flask(__name__, static_folder="static")

    @app.route("/")
    def index():
        return send_from_directory("static", "index.html")

    @app.route("/api/state")
    def api_state():
        # logging.debug(f"/api/state: refreshing states with {state_manager.get_state()}")
        return jsonify(state_manager.get_state())

    @app.route("/api/zones")
    def api_zones():
        return jsonify(state_manager.get_zone_states())

    # Zone configuration endpoints
    @app.route("/api/zone", methods=["GET"])
    def list_zone_configs():
        return jsonify(state_manager.zone_store.load_all())

    @app.route("/api/zone/<zone>", methods=["GET", "POST", "PUT", "DELETE"])
    def zone_config(zone):
        if request.method == "GET":
            data = state_manager.zone_store.load_all().get(zone)
            if data is None:
                abort(404)
            return jsonify(data)
        if request.method in ["POST", "PUT"]:
            state_manager.zone_store.save_zone(zone, request.json or {})
            return jsonify({"status": "ok"})
        if request.method == "DELETE":
            state_manager.zone_store.delete_zone(zone)
            return jsonify({"status": "ok"})

    return app

def graceful_exit(signum, frame):
    logging.info("Stopping program...")
    stop_mqtt()
    logging.info("Goodbye.")
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="Light relay controller")
    parser.add_argument("--config", help="Path to YAML configuration file")
    parser.add_argument("--log-level", help="Enforce debug level (DEBUG, INFO, WARNING, ERROR)")
    args = parser.parse_args()

    load_config(args.config)
    log_level = args.log_level or get_log_level()
    setup_logging(log_level)

    # MQTT thread
    global mqtt_thread
    mqtt_thread = threading.Thread(target=start_mqtt, args=(get_mqtt_config(),), daemon=True)
    mqtt_thread.start()

    dashboard_cfg = get_dashboard_config()

    if dashboard_cfg.get("enable", False):
        log = logging.getLogger("werkzeug")
        log.setLevel(log_level.upper())
        app = create_app()
        app.run(
            host=dashboard_cfg.get("bind", "0.0.0.0"),
            port=dashboard_cfg.get("port", 8080),
        )
    else:
        mqtt_thread.join()  # Keep running even without Flask
    

if __name__ == "__main__":
    signal.signal(signal.SIGINT, graceful_exit)
    signal.signal(signal.SIGTERM, graceful_exit)

    main()