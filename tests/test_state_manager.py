import logging
from state_manager import StateManager

# Mock send_tcp_command
tcp_log = []
def mock_send_tcp_command(ip, index, state):
    tcp_log.append((ip, index, state))

# Patch la fonction dans le module
import relay_controller
relay_controller.send_tcp_command = mock_send_tcp_command

def simulate_test():
    # Créer un StateManager avec une configuration factice
    manager = StateManager()
    manager.zone_config = {
        "Z1": {"ip": "127.0.0.1", "alarm": 1, "tamper": 2, "battery_low": 3, "offline": 4},
        "Z2": {"ip": "127.0.0.1", "alarm": 5, "tamper": 2, "battery_low": 3, "offline": 4},
    }

    # Capteur 1 déclenche une alarme
    logging.debug("Capteur 1 déclenche une alarme")
    manager.update_sensor("ABC123", "sensor1_Z1", {
        "alarm": True, "tamper": False, "battery_low": False, "alarm_expire": False
    })

    # Capteur 2 déclare une alarme
    logging.debug("Capteur 2 déclenche une alarme")
    manager.update_sensor("XYZ789", "sensor2_Z1", {
        "alarm": True, "tamper": False, "battery_low": False
    })

    # Capteur 2 fin d'alarme
    logging.debug("Capteur 2 fin d'alarme")
    manager.update_sensor("XYZ789", "sensor2_Z1", {
        "alarm": False, "tamper": False, "battery_low": True
    })
    # Capteur 1 fin d'alarme
    logging.debug("Capteur 1 fin d'alarme")
    manager.update_sensor("ABC123", "sensor1_Z1", {
        "alarm": False, "tamper": False, "battery_low": False, "alarm_expire": False
    })

    logging.debug("----- Z1 : Alarm=False, Bat Low = True -------")

    # Capteur 3 battery low
    logging.debug("Capteur 3 batterie faible")
    manager.update_sensor("DEF456", "sensor3_Z2", {
        "alarm": False, "tamper": False, "battery_low": True
    })

    # Capteur 2 fin batt low
    logging.debug("Capteur 2 fin batt low")
    manager.update_sensor("XYZ789", "sensor2_Z1", {
        "alarm": False, "tamper": False, "battery_low": False
    })

    # Capteur 3 battery low
    logging.debug("Capteur 3 din batterie faible")
    manager.update_sensor("DEF456", "sensor3_Z2", {
        "alarm": False, "tamper": False, "battery_low": False
    })

    # Capteur 3 de Z2 est hors ligne
    manager.state["DEF456"] = {
        "zone": "Z2", "dev_name": "sensor3_Z2",
        "alarm": False, "tamper": False, "battery_low": False,
        "last_seen": "2000-01-01T00:00:00Z"  # très ancien
    }

    manager._update_zone_status("Z2")

    print("Zone states:", manager.get_zone_states())
    print("TCP commands sent:")
    for cmd in tcp_log:
        print(cmd)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    simulate_test()
