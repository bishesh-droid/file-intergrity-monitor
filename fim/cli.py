import click
import sys
import os

from .monitor import FileIntegrityMonitor
from .database import DatabaseManager
from .logger import fim_logger
from .config import FIM_CONFIG_PATH, DATABASE_PATH

@click.group()
def cli():
    """
    File Integrity Monitor (FIM) CLI.
    Monitors files and directories for unauthorized changes.
    """
    pass

@cli.command(name="init")
@click.option('--config', '-c', type=click.Path(exists=True), default=FIM_CONFIG_PATH,
              help=f'Path to the FIM configuration YAML file (default: {FIM_CONFIG_PATH}).')
@click.option('--database', '-d', type=click.Path(), default=DATABASE_PATH,
              help=f'Path to the SQLite baseline database (default: {DATABASE_PATH}).')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing baseline database if it exists.')
def init_baseline(config, database, force):
    """
    Initializes the FIM baseline by scanning specified files and directories.
    """
    fim_logger.info(f"[*] Initializing FIM baseline using config: {config}")

    if os.path.exists(database) and not force:
        click.confirm(f"Baseline database '{database}' already exists. Overwrite?", abort=True)
        os.remove(database)
        fim_logger.warning(f"[WARN] Existing database '{database}' removed.")
    elif os.path.exists(database) and force:
        os.remove(database)
        fim_logger.warning(f"[WARN] Existing database '{database}' removed (forced).")

    db_manager = DatabaseManager(db_path=database)
    monitor = FileIntegrityMonitor(fim_config_path=config, db_manager=db_manager)

    try:
        monitor.create_baseline()
        click.echo("[+] FIM baseline created successfully.")
    except Exception as e:
        fim_logger.critical(f"[CRITICAL] Failed to create baseline: {e}")
        click.echo(f"Error: Failed to create baseline: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), default=FIM_CONFIG_PATH,
              help=f'Path to the FIM configuration YAML file (default: {FIM_CONFIG_PATH}).')
@click.option('--database', '-d', type=click.Path(), default=DATABASE_PATH,
              help=f'Path to the SQLite baseline database (default: {DATABASE_PATH}).')
def check(config, database):
    """
    Checks file integrity against the established baseline.
    """
    fim_logger.info(f"[*] Checking file integrity using config: {config} and database: {database}")

    if not os.path.exists(database):
        fim_logger.error(f"[ERROR] Baseline database not found at {database}. Please run 'fim init' first.")
        click.echo(f"Error: Baseline database not found at {database}. Please run 'fim init' first.", err=True)
        sys.exit(1)

    db_manager = DatabaseManager(db_path=database)
    monitor = FileIntegrityMonitor(fim_config_path=config, db_manager=db_manager)

    try:
        changes = monitor.check_integrity()
        
        click.echo("\n--- File Integrity Check Results ---")
        if not changes['added'] and not changes['modified'] and not changes['deleted']:
            click.echo("[+] No integrity violations detected. All monitored files are unchanged.")
        else:
            if changes['added']:
                click.echo("\n[!!!] Added Files:")
                for item in changes['added']:
                    click.echo(f"  - {item['file']} (Reason: {item['reason']})")
            if changes['modified']:
                click.echo("\n[!!!] Modified Files:")
                for item in changes['modified']:
                    click.echo(f"  - {item['file']} (Type: {item['type']})")
            if changes['deleted']:
                click.echo("\n[!!!] Deleted Files:")
                for item in changes['deleted']:
                    click.echo(f"  - {item['file']} (Reason: {item['reason']})")
        click.echo("------------------------------------")

    except Exception as e:
        fim_logger.critical(f"[CRITICAL] Failed to check integrity: {e}")
        click.echo(f"Error: Failed to check integrity: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--database', '-d', type=click.Path(), default=DATABASE_PATH,
              help=f'Path to the SQLite baseline database (default: {DATABASE_PATH}).')
def status(database):
    """
    Displays the status of the FIM baseline.
    """
    fim_logger.info(f"[*] Checking FIM baseline status for database: {database}")

    if not os.path.exists(database):
        click.echo(f"[!] Baseline database not found at {database}. No baseline established.")
        sys.exit(0)

    db_manager = DatabaseManager(db_path=database)
    all_paths = db_manager.get_all_baseline_paths()
    click.echo(f"\n--- FIM Baseline Status ---")
    click.echo(f"Baseline Database: {database}")
    click.echo(f"Monitored Files in Baseline: {len(all_paths)}")
    click.echo("---------------------------")

if __name__ == '__main__':
    cli()
