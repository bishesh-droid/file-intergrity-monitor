import sqlite3
import os
import time

from .config import DATABASE_PATH
from .logger import fim_logger

class DatabaseManager:
    """
    Manages SQLite database operations for storing and retrieving file baseline data.
    """
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self.conn = None
        self._init_db()

    def __del__(self):
        """
        Destructor to ensure the database connection is closed.
        """
        if self.conn:
            self.conn.close()
            fim_logger.info("[*] FIM Database connection closed.")

    def _get_connection(self):
        """
        Returns the existing database connection or creates a new one.
        """
        if self.conn is None:
            try:
                self.conn = sqlite3.connect(self.db_path)
                self.conn.row_factory = sqlite3.Row
                fim_logger.info(f"[*] FIM Database connection opened to {self.db_path}")
            except sqlite3.Error as e:
                fim_logger.critical(f"[CRITICAL] FIM Database connection failed: {e}")
                raise
        return self.conn

    def _init_db(self):
        """
        Initializes the database by creating the necessary table if it doesn't exist.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitored_files (
                    file_path TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    modification_time REAL NOT NULL,
                    creation_time REAL NOT NULL,
                    permissions INTEGER NOT NULL,
                    baseline_timestamp REAL NOT NULL
                )
            """)
            conn.commit()
            fim_logger.info(f"[*] FIM Database initialized at {self.db_path}")
        except sqlite3.Error as e:
            fim_logger.critical(f"[CRITICAL] FIM Database initialization failed: {e}")

    def save_baseline_entry(self, file_path: str, file_hash: str, file_size: int, modification_time: float, creation_time: float, permissions: int):
        """
        Saves or updates a file's baseline entry in the database.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            baseline_timestamp = time.time()
            cursor.execute("""
                INSERT OR REPLACE INTO monitored_files 
                (file_path, file_hash, file_size, modification_time, creation_time, permissions, baseline_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (file_path, file_hash, file_size, modification_time, creation_time, permissions, baseline_timestamp))
            conn.commit()
            fim_logger.debug(f"[DB] Saved baseline for {file_path}")
        except sqlite3.Error as e:
            fim_logger.error(f"[DB_ERROR] Failed to save baseline for {file_path}: {e}")

    def get_baseline_entry(self, file_path: str) -> dict | None:
        """
        Retrieves a file's baseline entry from the database.

        Returns:
            dict or None: A dictionary containing file info, or None if not found.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM monitored_files WHERE file_path = ?", (file_path,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            fim_logger.error(f"[DB_ERROR] Failed to retrieve baseline for {file_path}: {e}")
            raise

    def get_all_baseline_paths(self) -> set[str]:
        """
        Returns a set of all file paths currently in the baseline.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT file_path FROM monitored_files")
            return {row[0] for row in cursor.fetchall()}
        except sqlite3.Error as e:
            fim_logger.error(f"[DB_ERROR] Failed to get all baseline paths: {e}")
            raise

    def remove_baseline_entry(self, file_path: str):
        """
        Removes a file's baseline entry from the database.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM monitored_files WHERE file_path = ?", (file_path,))
            conn.commit()
            fim_logger.debug(f"[DB] Removed baseline for {file_path}")
        except sqlite3.Error as e:
            fim_logger.error(f"[DB_ERROR] Failed to remove baseline for {file_path}: {e}")