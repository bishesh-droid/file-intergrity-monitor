import hashlib
import os

from .logger import fim_logger

def calculate_file_hash(file_path: str, algorithm: str = "sha256") -> str:
    """
    Computes the cryptographic hash of a file.

    Args:
        file_path (str): The path to the file.
        algorithm (str): The hashing algorithm to use (e.g., "sha256", "sha512", "md5").

    Returns:
        str: The hexadecimal representation of the file's hash.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If an unsupported hashing algorithm is specified.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    algorithm = algorithm.lower()
    if algorithm not in hashlib.algorithms_available:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    hasher = hashlib.new(algorithm)
    
    fim_logger.debug(f"[*] Hashing file '{file_path}' with {algorithm}...")
    try:
        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        file_hash = hasher.hexdigest()
        fim_logger.debug(f"[+] File hash generated for {file_path}: {file_hash}")
        return file_hash
    except FileNotFoundError:
        fim_logger.error(f"[ERROR] File not found during hashing: {file_path}")
        raise
    except Exception as e:
        fim_logger.error(f"[ERROR] Failed to hash file {file_path}: {e}")
        raise