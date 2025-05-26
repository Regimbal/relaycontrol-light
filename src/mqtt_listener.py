import yaml, importlib, re, logging, time, json
import paho.mqtt.client as mqtt
from config_loader import get_mqtt_config
from state_manager import update_state

logger = logging.getLogger(__name__)

client = mqtt.Client(client_id="relaycontroller")
mqtt_cfg = get_mqtt_config()

def connect_with_retries(client, host, port, keepalive, retry_interval=5):
    while True:
        try:
            client.connect(host, port, keepalive)
            logging.info(f"Successfully connected to MQTT broker {host}:{port}")
            return
        except Exception as e:
            logging.error(f"Failed to connect to MQTT broker : {e}")
            logging.info(f"New attempt in {retry_interval} secs...")
            time.sleep(retry_interval)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"MQTT successfully connected with code {rc}")
        client.subscribe(mqtt_cfg["topic"])
        logger.info(f"Subscribed to topic {mqtt_cfg['topic']}")
    else:
        logger.error(f"Failed to connect to MQTT broker, return code {rc}")

def on_disconnect(client, userdata, rc):
    logger.warning("Disconnected from MQTT Broker")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        logging.debug(f"{payload}")
        dev_eui = payload.get("devEUI")
    except Exception as e:
        logging.error(f"Error while processing MQTT message: {e}")

def start_mqtt():
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
    client.disconnect()