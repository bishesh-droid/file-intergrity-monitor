import os
import time
import json
import yaml
from typing import List, Dict, Any

from .logger import fim_logger
from .config import HASH_ALGORITHM, FIM_CONFIG_PATH
from .hasher import calculate_file_hash
from .database import DatabaseManager

class FileIntegrityMonitor:
    """
    Monitors file and directory integrity by comparing current state to a baseline.
    """
    def __init__(self, fim_config_path: str = FIM_CONFIG_PATH, db_manager: DatabaseManager = None):
        self.fim_config_path = fim_config_path
        self.db_manager = db_manager if db_manager else DatabaseManager()
        self.monitored_paths = {'include': [], 'exclude': []}
        self._load_fim_config()
        fim_logger.info(f"[*] FIM initialized. Monitoring config from: {self.fim_config_path}")

    def _load_fim_config(self):
        """
        Loads the FIM configuration from a YAML file.
        """
        if not os.path.exists(self.fim_config_path):
            fim_logger.warning(f"[WARN] FIM config file not found at {self.fim_config_path}. Using empty config.")
            return
        try:
            with open(self.fim_config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.monitored_paths['include'] = config.get('include', [])
                self.monitored_paths['exclude'] = config.get('exclude', [])
            fim_logger.info(f"[*] Loaded FIM configuration: {len(self.monitored_paths['include'])} include paths, {len(self.monitored_paths['exclude'])} exclude paths.")
        except yaml.YAMLError as e:
            fim_logger.error(f"[ERROR] Error parsing FIM config file {self.fim_config_path}: {e}")
        except Exception as e:
            fim_logger.error(f"[ERROR] Unexpected error loading FIM config: {e}")

    def _is_path_monitored(self, file_path: str) -> bool:
        """
        Checks if a file path should be monitored based on include/exclude rules.
        """
        # Check exclude rules first
        for exclude_path in self.monitored_paths['exclude']:
            if file_path.startswith(os.path.abspath(exclude_path)):
                return False
        # Check include rules
        for include_path in self.monitored_paths['include']:
            if file_path.startswith(os.path.abspath(include_path)):
                return True
        return False

    def _get_file_metadata(self, file_path: str) -> Dict[str, Any] | None:
        """
        Retrieves metadata for a file.
        """
        try:
            stat = os.stat(file_path)
            return {
                'file_path': file_path,
                'file_size': stat.st_size,
                'modification_time': stat.st_mtime,
                'creation_time': stat.st_ctime,
                'permissions': stat.st_mode & 0o777 # Get only permission bits
            }
        except FileNotFoundError:
            return None
        except Exception as e:
            fim_logger.error(f"[ERROR] Failed to get metadata for {file_path}: {e}")
            return None

    def create_baseline(self):
        """
        Scans specified directories, computes hashes and metadata, and saves them to the database.
        """
        fim_logger.info("[*] Creating new FIM baseline...")
        monitored_count = 0
        for include_path in self.monitored_paths['include']:
            abs_include_path = os.path.abspath(include_path)
            if not os.path.exists(abs_include_path):
                fim_logger.warning(f"[WARN] Include path '{abs_include_path}' does not exist. Skipping.")
                continue

            for root, _, files in os.walk(abs_include_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    if self._is_path_monitored(file_path):
                        try:
                            file_hash = calculate_file_hash(file_path, HASH_ALGORITHM)
                            metadata = self._get_file_metadata(file_path)
                            if metadata and file_hash:
                                self.db_manager.save_baseline_entry(
                                    file_path=file_path,
                                    file_hash=file_hash,
                                    file_size=metadata['file_size'],
                                    modification_time=metadata['modification_time'],
                                    creation_time=metadata['creation_time'],
                                    permissions=metadata['permissions']
                                )
                                monitored_count += 1
                        except Exception as e:
                            fim_logger.error(f"[ERROR] Failed to process {file_path} for baseline: {e}")
        fim_logger.info(f"[+] Baseline created with {monitored_count} files.")

    def check_integrity(self) -> Dict[str, Any]:
        """
        Compares current file states to the baseline and reports changes.

        Returns:
            dict: A dictionary containing lists of added, modified, and deleted files.
        """
        fim_logger.info("[*] Checking file integrity against baseline...")
        changes = {'added': [], 'modified': [], 'deleted': []}
        
        baseline_paths = self.db_manager.get_all_baseline_paths()
        current_paths = set()

        # First, build a set of all currently monitored paths
        for include_path in self.monitored_paths['include']:
            abs_include_path = os.path.abspath(include_path)
            if not os.path.exists(abs_include_path):
                continue
            for root, _, files in os.walk(abs_include_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    if self._is_path_monitored(file_path):
                        current_paths.add(file_path)

        # Identify added and deleted files
        added_files = current_paths - baseline_paths
        deleted_files = baseline_paths - current_paths

        for file_path in added_files:
            changes['added'].append({'file': file_path, 'reason': 'New file not in baseline'})
            fim_logger.info(f"[ADDED] New file detected: {file_path}")

        for file_path in deleted_files:
            changes['deleted'].append({'file': file_path, 'reason': 'File deleted from monitored path'})
            fim_logger.warning(f"[DELETED] File deleted: {file_path}")

        # Check for modifications in files that are in both baseline and current paths
        for file_path in baseline_paths.intersection(current_paths):
            current_metadata = self._get_file_metadata(file_path)
            if not current_metadata:
                continue  # Skip if metadata can't be retrieved

            baseline_entry = self.db_manager.get_baseline_entry(file_path)
            if not baseline_entry:
                # This case is unlikely but handled for safety
                changes['added'].append({'file': file_path, 'reason': 'File exists but is not in baseline'})
                fim_logger.info(f"[ADDED] New file detected (edge case): {file_path}")
                continue

            # Check for metadata and hash changes
            try:
                if current_metadata['file_size'] != baseline_entry['file_size']:
                    changes['modified'].append({'file': file_path, 'type': 'size_mismatch', 'old_size': baseline_entry['file_size'], 'new_size': current_metadata['file_size']})
                    fim_logger.warning(f"[MODIFIED] Size mismatch for {file_path}")
                elif current_metadata['modification_time'] != baseline_entry['modification_time']:
                    changes['modified'].append({'file': file_path, 'type': 'mtime_mismatch', 'old_mtime': baseline_entry['modification_time'], 'new_mtime': current_metadata['modification_time']})
                    fim_logger.warning(f"[MODIFIED] Modification time mismatch for {file_path}")
                elif current_metadata['permissions'] != baseline_entry['permissions']:
                    changes['modified'].append({'file': file_path, 'type': 'permissions_mismatch', 'old_perms': oct(baseline_entry['permissions']), 'new_perms': oct(current_metadata['permissions'])})
                    fim_logger.warning(f"[MODIFIED] Permissions mismatch for {file_path}")
                else:
                    # Only calculate hash if metadata is unchanged
                    current_hash = calculate_file_hash(file_path, HASH_ALGORITHM)
                    if current_hash != baseline_entry['file_hash']:
                        changes['modified'].append({'file': file_path, 'type': 'hash_mismatch', 'old_hash': baseline_entry['file_hash'], 'new_hash': current_hash})
                        fim_logger.warning(f"[MODIFIED] Hash mismatch for {file_path}")
            except Exception as e:
                fim_logger.error(f"[ERROR] Error checking {file_path} for modifications: {e}")

        fim_logger.info("[+] Integrity check complete.")
        return changes