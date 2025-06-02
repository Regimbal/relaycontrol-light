# relay_controller.py
import socket
import logging

logger = logging.getLogger(__name__)


def send_tcp_command(ip: str, relay_index: int, state: bool):
    """
    Send TCP request to enable / disable a relay.
    Request format : "SR <index> on|off"
    waits for the target to ack and close socket.
    """
    command = f"SR {relay_index} {'on' if state else 'off'}\n"
    logger.debug(f"[RELAY] Sending relay {relay_index} @ {ip}: {command}")
    try:
        with socket.create_connection((ip, 17123), timeout=2) as sock:
            sock.sendall(command.encode("utf-8"))
            # Lecture de la réponse (accusé de réception)
            ack = sock.recv(1024).decode("utf-8").strip()
            logger.info(f"[RELAY] Received ack from {ip}: {ack}")
        logger.info(f"[RELAY] Request sent to {ip} : {command.strip()}")
    except Exception as e:
        logger.error(f"[RELAY] Fail sending relay {relay_index} @ {ip}: {e}")


# Optionnel : mémo pour future extension (ex: status, groups...)
# def query_relay_status(ip: str):
#     pass
