"""SQLite-based persistence for sensor states."""

import sqlite3
import json
import os
import logging
import threading

class SQLiteStateStore:
    """Store and retrieve sensor state from an SQLite database."""
    def __init__(self, db_path="state.db", json_path="state.json"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_db()
        if json_path:
            self.migrate_from_json()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS sensors (
                        dev_eui TEXT PRIMARY KEY,
                        dev_name TEXT,
                        zone TEXT,
                        last_seen TEXT,
                        alarm INTEGER,
                        tamper INTEGER,
                        battery_low INTEGER,
                        offline INTEGER
                    )
                ''')
        except sqlite3.OperationalError as e:
            logging.error(f"SQLite error during DB init: {e}")
            raise

    def load_all(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row  # pour accéder par noms de colonnes
            cursor = conn.execute("SELECT * FROM sensors")
            return {
                row["dev_eui"]: {
                    "dev_name": row["dev_name"],
                    "zone": row["zone"],
                    "last_seen": row["last_seen"],
                    "alarm": bool(row["alarm"]),
                    "tamper": bool(row["tamper"]),
                    "battery_low": bool(row["battery_low"]),
                    "offline": bool(row["offline"]),
                }
                for row in cursor.fetchall()
            }

    def save_sensor(self, dev_eui, state: dict):
        with self.lock, sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO sensors (dev_eui, dev_name, zone, last_seen, alarm, tamper, battery_low, offline)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dev_eui) DO UPDATE SET
                    dev_name=excluded.dev_name,
                    zone=excluded.zone,
                    last_seen=excluded.last_seen,
                    alarm=excluded.alarm,
                    tamper=excluded.tamper,
                    battery_low=excluded.battery_low,
                    offline=excluded.offline
            ''', (
                dev_eui,
                state.get("dev_name"),
                state.get("zone"),
                state.get("last_seen"),
                int(state.get("alarm", 0)),
                int(state.get("tamper", 0)),
                int(state.get("battery_low", 0)),
                int(state.get("offline", 0)),
            ))

    def migrate_from_json(self, json_path="state.json"):
        if not os.path.exists(json_path):
            logging.info("No json state file to migrate.")
            return

        logging.info("Migrating state.json to SQLite...")
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
            with sqlite3.connect(self.db_path) as conn:
                for dev_eui, entry in data.items():
                    conn.execute("""
                        INSERT OR REPLACE INTO sensors (dev_eui, dev_name, zone, alarm, tamper, battery_low, offline, last_seen)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        dev_eui,
                        entry.get("dev_name"),
                        entry.get("zone"),
                        entry.get("alarm", False),
                        entry.get("tamper", False),
                        entry.get("battery_low", False),
                        entry.get("offline", False),
                        entry.get("last_seen"),
                    ))
            os.rename(json_path, json_path + ".migrated")
            logging.info("Migration successfully ended. JSON file renamed .migrated")
        except Exception as e:
            logging.error(f"Error during JSON → SQLite migration: {e}")