"""MQTT listener that decodes messages and updates the StateManager."""

import yaml
import importlib
import re
import logging
import time
import json
import base64
import paho.mqtt.client as mqtt
from state_manager import StateManager
from state_manager_instance import state_manager

client = mqtt.Client(client_id="relaycontroller")
mqtt_cfg = None

def connect_with_retries(client, host, port, keepalive, retry_interval=5):
    """Connect to the broker and retry forever on failure."""
    while True:
        try:
            client.connect(host, port, keepalive)
            logging.info(f"Successfully connected to MQTT broker {host}:{port}")
            return
        except Exception as e:
            logging.error(f"Failed to connect to MQTT broker : {e}")
            logging.error(f"New attempt in {retry_interval} secs...")
            time.sleep(retry_interval)

def on_connect(client, userdata, flags, rc):
    """Subscribe to the configured topic once the broker connection succeeds."""
    if rc == 0:
        logging.info(f"MQTT successfully connected with code {rc}")
        client.subscribe(mqtt_cfg["topic"])
        logging.info(f"Subscribed to topic {mqtt_cfg['topic']}")
    else:
        logging.error(f"Failed to connect to MQTT broker, return code {rc}")

def on_disconnect(client, userdata, rc):
    """Log unexpected disconnection."""
    logging.warning("Disconnected from MQTT Broker")

def on_message(client, userdata, msg):
    """Decode an incoming message and forward it to the state manager."""
    try:
        payload = json.loads(msg.payload.decode())
        logging.debug(f"Received message: {payload}")
        dev_eui = payload.get("devEUI")
        dev_name = payload.get("deviceName")
        codec_name = payload.get("applicationName")
        data_encode = payload.get("data_encode", "")

        if data_encode in ("", "hexstring"):
            data = payload.get("data", "")
            payload_bytes = bytes.fromhex(data)
        elif data_encode == "base64":
            data = payload.get("data", "")
            payload_bytes = base64.b64decode(data)
        else:
            logging.error(
                f"Ignored message from {dev_eui} (data_encode={data_encode}) unsupported"
            )
            return
        
        codec = importlib.import_module(f"codec.{codec_name}")
        data_decoded = codec.decode(payload_bytes)
        logging.debug(f"{dev_eui}: decoded payload is {data_decoded}")

        state_manager.update_sensor(dev_eui, dev_name, data_decoded)

    except Exception as e:
        logging.error(f"Error while processing MQTT message: {e}")

def start_mqtt(cfg=None):
    """Start the MQTT loop with the provided configuration."""
    global mqtt_cfg
    # configuration file loaded by the main program. A configuration
    # dictionary can be passed directly for testing purposes.
    mqtt_cfg = cfg

     # Authentification utilisateur
    username = mqtt_cfg.get("username")
    password = mqtt_cfg.get("password")
    if username and password:
        client.username_pw_set(username, password)

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    broker = mqtt_cfg["broker"]
    port = mqtt_cfg.get("port", 8883 if mqtt_cfg.get("use_tls", False) else 1883)

    connect_with_retries(client, broker, port, keepalive=60)
    client.loop_forever()

def stop_mqtt():
    """Disconnect from the MQTT broker."""
    client.disconnect()