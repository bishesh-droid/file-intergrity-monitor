# File Integrity Monitor (FIM)

A command-line File Integrity Monitor (FIM) in Python. This tool establishes a baseline hash for designated files and directories. It subsequently identifies any unauthorized modifications, additions, or deletions, and logs these events. Its configuration is managed through a YAML file, and it utilizes a database to maintain the integrity baseline.

## Features

-   **Baseline Creation**: Create a baseline of file hashes and metadata.
-   **Integrity Checking**: Compare files against the baseline to detect changes.
-   **Configurable**: Specify files and directories to include or exclude using a YAML configuration file.
-   **Multiple Hash Algorithms**: Supports `sha256`, `sha512`, `md5`, and `sha1`.
-   **Logging**: Detailed logging of all operations.
-   **CLI**: Easy-to-use command-line interface.

## Getting Started

### Prerequisites

-   Python 3.x
-   pip

### Installation

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    ```
2.  Navigate to the project directory:
    ```bash
    cd 038_file_integrity_monitor
    ```
3.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

The FIM tool provides three main commands: `init`, `check`, and `status`.

### `init`

Initializes the FIM baseline by scanning specified files and directories.

```bash
python -m fim.cli init [OPTIONS]
```

**Options:**

-   `--config, -c`: Path to the FIM configuration YAML file (default: `config/fim_config.yaml`).
-   `--database, -d`: Path to the SQLite baseline database (default: `data/fim_baseline.db`).
-   `--force, -f`: Overwrite existing baseline database if it exists.

### `check`

Checks file integrity against the established baseline.

```bash
python -m fim.cli check [OPTIONS]
```

**Options:**

-   `--config, -c`: Path to the FIM configuration YAML file (default: `config/fim_config.yaml`).
-   `--database, -d`: Path to the SQLite baseline database (default: `data/fim_baseline.db`).

### `status`

Displays the status of the FIM baseline.

```bash
python -m fim.cli status [OPTIONS]
```

**Options:**

-   `--database, -d`: Path to the SQLite baseline database (default: `data/fim_baseline.db`).

## Configuration

The FIM tool is configured using a YAML file (e.g., `config/fim_config.yaml`).

```yaml
# List of files and directories to monitor.
include:
  - /path/to/monitor1
  - /path/to/monitor2

# List of files and directories to exclude from monitoring.
exclude:
  - /path/to/exclude1

# Hashing algorithm to use.
# Supported options: 'sha256', 'sha512', 'md5', 'sha1'
hash_algorithm: sha256

# Log level for the FIM application.
# Options: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
log_level: INFO

# Whether to show verbose output in the console.
verbose_console_output: true
```

## Development

### Running Tests

To run the tests, use `pytest`:

```bash
pytest
```
