import unittest
from unittest.mock import patch, MagicMock
import os
import shutil
import time
import hashlib
import yaml
import sqlite3

from fim.config import HASH_ALGORITHM
from fim.hasher import calculate_file_hash
from fim.database import DatabaseManager
from fim.monitor import FileIntegrityMonitor

class TestHasher(unittest.TestCase):

    def setUp(self):
        self.test_dir = "test_hasher_dir"
        os.makedirs(self.test_dir, exist_ok=True)
        self.test_file = os.path.join(self.test_dir, "test_hash_file.txt")
        with open(self.test_file, 'w') as f:
            f.write("This is content for hashing.")
        # Mock logger
        patch('fim.hasher.fim_logger').start()
        self.addCleanup(patch.stopall)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_calculate_file_hash_sha256(self):
        expected_hash = hashlib.sha256(b"This is content for hashing.").hexdigest()
        self.assertEqual(calculate_file_hash(self.test_file, "sha256"), expected_hash)

    def test_calculate_file_hash_sha512(self):
        expected_hash = hashlib.sha512(b"This is content for hashing.").hexdigest()
        self.assertEqual(calculate_file_hash(self.test_file, "sha512"), expected_hash)

    def test_calculate_file_hash_not_found(self):
        with self.assertRaises(FileNotFoundError):
            calculate_file_hash("non_existent_file.txt")

    def test_calculate_file_hash_unsupported_algo(self):
        with self.assertRaises(ValueError):
            calculate_file_hash(self.test_file, "unsupported_algo")

class TestDatabaseManager(unittest.TestCase):

    def setUp(self):
        self.test_db_path = ":memory:" # Use in-memory database for testing
        self.db_manager = DatabaseManager(db_path=self.test_db_path)
        # Mock logger
        patch('fim.database.fim_logger').start()
        self.addCleanup(patch.stopall)

    def test_init_db(self):
        conn = self.db_manager._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monitored_files';")
        self.assertIsNotNone(cursor.fetchone())

    def test_save_get_baseline_entry(self):
        file_path = "/test/file.txt"
        file_hash = "abcdef123"
        file_size = 100
        mtime = time.time()
        ctime = time.time()
        perms = 0o644

        self.db_manager.save_baseline_entry(file_path, file_hash, file_size, mtime, ctime, perms)
        entry = self.db_manager.get_baseline_entry(file_path)

        self.assertIsNotNone(entry)
        self.assertEqual(entry['file_path'], file_path)
        self.assertEqual(entry['file_hash'], file_hash)
        self.assertEqual(entry['file_size'], file_size)

    def test_get_all_baseline_paths(self):
        self.db_manager.save_baseline_entry("/test/file1.txt", "h1", 1, 1, 1, 1)
        self.db_manager.save_baseline_entry("/test/file2.txt", "h2", 2, 2, 2, 2)
        paths = self.db_manager.get_all_baseline_paths()
        self.assertEqual(paths, {"/test/file1.txt", "/test/file2.txt"})

    def test_get_baseline_entry_error(self):
        with patch.object(self.db_manager, '_get_connection') as mock_conn:
            mock_conn.return_value.cursor.return_value.execute.side_effect = sqlite3.Error
            with self.assertRaises(sqlite3.Error):
                self.db_manager.get_baseline_entry("/test/file.txt")

    def test_remove_baseline_entry(self):
        file_path = "/test/file.txt"
        self.db_manager.save_baseline_entry(file_path, "h1", 1, 1, 1, 1)
        self.db_manager.remove_baseline_entry(file_path)
        self.assertIsNone(self.db_manager.get_baseline_entry(file_path))

    def test_get_all_baseline_paths_error(self):
        with patch.object(self.db_manager, '_get_connection') as mock_conn:
            mock_conn.return_value.cursor.return_value.execute.side_effect = sqlite3.Error
            with self.assertRaises(sqlite3.Error):
                self.db_manager.get_all_baseline_paths()

class TestFileIntegrityMonitor(unittest.TestCase):

    def setUp(self):
        self.test_dir = os.path.abspath("test_fim_monitor_dir")
        self.monitored_path = os.path.join(self.test_dir, "monitored")
        self.excluded_path = os.path.join(self.monitored_path, "excluded")
        os.makedirs(self.monitored_path, exist_ok=True)
        os.makedirs(self.excluded_path, exist_ok=True)

        self.fim_config_path = os.path.join(self.test_dir, "fim_config.yaml")
        self.fim_config_content = {
            'include': [self.monitored_path],
            'exclude': [self.excluded_path]
        }
        with open(self.fim_config_path, 'w') as f:
            yaml.dump(self.fim_config_content, f)

        self.test_db_path = os.path.join(self.test_dir, "test_fim.db")
        self.db_manager = DatabaseManager(db_path=self.test_db_path)
        self.monitor = FileIntegrityMonitor(fim_config_path=self.fim_config_path, db_manager=self.db_manager)

        # Mock logger
        patch('fim.monitor.fim_logger').start()
        self.addCleanup(patch.stopall)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_test_file(self, sub_path, content="initial content"):
        file_path = os.path.join(self.monitored_path, sub_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
        return os.path.abspath(file_path)

    def test_is_path_monitored(self):
        monitored_file = self._create_test_file("file.txt")
        excluded_file = os.path.join(self.excluded_path, "excluded.txt")
        with open(excluded_file, 'w') as f: f.write("content")

        self.assertTrue(self.monitor._is_path_monitored(monitored_file))
        self.assertFalse(self.monitor._is_path_monitored(os.path.abspath(excluded_file)))
        self.assertFalse(self.monitor._is_path_monitored("/tmp/unmonitored.txt"))

    def test_create_baseline(self):
        file1 = self._create_test_file("file1.txt")
        file2 = self._create_test_file("subdir/file2.txt")
        excluded_file = os.path.join(self.excluded_path, "excluded.txt")
        with open(excluded_file, 'w') as f: f.write("content")

        self.monitor.create_baseline()
        
        self.assertIsNotNone(self.db_manager.get_baseline_entry(file1))
        self.assertIsNotNone(self.db_manager.get_baseline_entry(file2))
        self.assertIsNone(self.db_manager.get_baseline_entry(os.path.abspath(excluded_file)))
        self.assertEqual(len(self.db_manager.get_all_baseline_paths()), 2)

    def test_check_integrity_no_changes(self):
        file1 = self._create_test_file("file1.txt")
        self.monitor.create_baseline()
        changes = self.monitor.check_integrity()
        self.assertEqual(len(changes['added']), 0)
        self.assertEqual(len(changes['modified']), 0)
        self.assertEqual(len(changes['deleted']), 0)

    def test_check_integrity_modified_file(self):
        file1 = self._create_test_file("file1.txt")
        self.monitor.create_baseline()
        
        # Modify file content
        with open(file1, 'a') as f:
            f.write("new content")
        
        changes = self.monitor.check_integrity()
        self.assertEqual(len(changes['modified']), 1)
        self.assertEqual(changes['modified'][0]['file'], file1)
        self.assertEqual(changes['modified'][0]['type'], 'size_mismatch')

    def test_check_integrity_added_file(self):
        self.monitor.create_baseline()
        file2 = self._create_test_file("file2.txt") # Add after baseline
        
        changes = self.monitor.check_integrity()
        self.assertEqual(len(changes['added']), 1)
        self.assertEqual(changes['added'][0]['file'], file2)

    def test_check_integrity_deleted_file(self):
        file1 = self._create_test_file("file1.txt")
        self.monitor.create_baseline()
        
        os.remove(file1) # Delete after baseline

        changes = self.monitor.check_integrity()
        self.assertEqual(len(changes['deleted']), 1)
        self.assertEqual(changes['deleted'][0]['file'], file1)

if __name__ == '__main__':
    unittest.main()