import sqlite3, yaml, os, logging
import threading

class SQLiteZoneStore:
    def __init__(self, db_path="state.db", yaml_path="config/zones.yaml"):
        self.db_path = db_path
        self.yaml_path = yaml_path
        self.lock = threading.Lock()
        self._init_db()
        if yaml_path:
            self.migrate_from_yaml()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS zones (
                        zone TEXT PRIMARY KEY,
                        ip TEXT,
                        alarm INTEGER,
                        tamper INTEGER,
                        battery_low INTEGER,
                        conn_issue INTEGER
                    )
                    """
                )
        except sqlite3.OperationalError as e:
            logging.error(f"SQLite error during zone DB init: {e}")
            raise

    def load_all(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM zones")
            return {
                row["zone"]: {
                    "ip": row["ip"],
                    "alarm": row["alarm"],
                    "tamper": row["tamper"],
                    "battery_low": row["battery_low"],
                    "conn_issue": row["conn_issue"],
                }
                for row in cursor.fetchall()
            }

    def migrate_from_yaml(self):
        if not os.path.exists(self.yaml_path):
            return
        logging.info("Migrating zones.yaml to SQLite...")
        try:
            with open(self.yaml_path, "r") as f:
                data = yaml.safe_load(f) or {}
            with sqlite3.connect(self.db_path) as conn:
                for zone, config in data.items():
                    if zone.startswith("__"):
                        continue
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO zones (zone, ip, alarm, tamper, battery_low, conn_issue)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            zone,
                            config.get("ip"),
                            config.get("alarm"),
                            config.get("tamper"),
                            config.get("low_batt") or config.get("battery_low"),
                            config.get("conn_issue"),
                        ),
                    )
            os.rename(self.yaml_path, self.yaml_path + ".migrated")
            logging.info("zones.yaml migrated to SQLite")
        except Exception as e:
            logging.error(f"Error migrating zones YAML: {e}")
            raise