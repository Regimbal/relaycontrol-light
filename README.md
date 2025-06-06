# Relay Control Light

This project controls relays via MQTT messages and exposes a small Flask dashboard.

## Usage with Docker Compose

A `docker-compose.yml` is provided to run a local Mosquitto broker along with the application.

```bash
docker-compose up --build
```

The dashboard will be available on `http://localhost:8080` and the broker on port `1883`.

### Configuration

Edit `config/config.yaml` before starting the containers. In the `mqtt` section set the broker host to `mosquitto` so the application can reach the broker service:

```yaml
mqtt:
  broker: "mosquitto"
```

Additional parameters such as port or topics can also be tweaked in this file.