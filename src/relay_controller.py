"""Utility for sending TCP commands to relay controllers."""
import socket
import logging

def send_tcp_command(ip: str, relay_index: int, state: bool):
    """Send a TCP command to toggle a relay on the target device."""
    command = f"SR {relay_index} {'on' if state else 'off'}\n"
    logging.debug(f"[RELAY] Sending relay {relay_index} @ {ip}: {command}")
    try:
        with socket.create_connection((ip, 17123), timeout=2) as sock:
            sock.sendall(command.encode("utf-8"))
            # Lecture de la réponse (accusé de réception)
            ack = sock.recv(1024).decode("utf-8").strip()
            logging.info(f"[RELAY] Received ack from {ip}: {ack}")
        logging.info(f"[RELAY] Request sent to {ip} : {command.strip()}")
    except Exception as e:
        logging.error(f"[RELAY] Fail sending relay {relay_index} @ {ip}: {e}")


# Optionnel : mémo pour future extension (ex: status, groups...)
# def query_relay_status(ip: str):
#     pass
