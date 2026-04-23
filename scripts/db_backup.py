"""
Database backup script for RiskMate.

Exports each table from a SQLite database to CSV files, bundles them into
a dated ZIP file, and prunes old backups. Intended to be run as a scheduled
task on PythonAnywhere or similar.

Usage examples:
  python scripts/db_backup.py
  python scripts/db_backup.py --db /home/username/project/db.sqlite3 --out-dir /home/username/backups --keep-days 14

The script defaults to the repository root `db.sqlite3` if available.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import os
import shutil
import sqlite3
import sys
import zipfile
from typing import Iterable, List


def default_db_path() -> str:
    # Default to repo root db.sqlite3 (one level up from scripts/)
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base, "db.sqlite3")


def list_tables(conn: sqlite3.Connection) -> List[str]:
    cur = conn.cursor()
    cur.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    return [row[0] for row in cur.fetchall()]


def export_table_to_csv(conn: sqlite3.Connection, table: str, out_path: str) -> None:
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM \"{table}\"")
    rows = cur.fetchall()
    headers = [d[0] for d in cur.description] if cur.description else []

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if headers:
            writer.writerow(headers)
        writer.writerows(rows)


def export_schema(conn: sqlite3.Connection, out_path: str) -> None:
    cur = conn.cursor()
    cur.execute("SELECT sql FROM sqlite_master WHERE type IN ('table','index','trigger','view') AND sql IS NOT NULL")
    stmts = [row[0] for row in cur.fetchall() if row[0]]
    with open(out_path, "w", encoding="utf-8") as f:
        for s in stmts:
            f.write(s.rstrip())
            f.write(";\n\n")


def make_zip(source_dir: str, zip_path: str) -> None:
    # Create a zip file from the directory contents
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(source_dir):
            for fn in files:
                full = os.path.join(root, fn)
                arcname = os.path.relpath(full, start=source_dir)
                zf.write(full, arcname)


def prune_old_backups(out_root: str, keep_days: int) -> None:
    if keep_days <= 0:
        return
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=keep_days)
    for name in os.listdir(out_root):
        path = os.path.join(out_root, name)
        if not os.path.isfile(path):
            continue
        try:
            mtime = datetime.datetime.utcfromtimestamp(os.path.getmtime(path))
        except OSError:
            continue
        if mtime < cutoff:
            try:
                os.remove(path)
                print(f"Removed old backup: {path}")
            except OSError:
                print(f"Failed to remove old backup: {path}")


def run_backup(db_path: str, out_dir: str, keep_days: int) -> int:
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return 2

    date_str = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H%M%SZ")
    backup_subdir = os.path.join(out_dir, f"backup_{date_str}")
    os.makedirs(backup_subdir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        tables = list_tables(conn)
        print(f"Found tables: {tables}")

        for table in tables:
            out_path = os.path.join(backup_subdir, f"{table}.csv")
            print(f"Exporting table {table} -> {out_path}")
            try:
                export_table_to_csv(conn, table, out_path)
            except Exception as e:
                print(f"Failed exporting {table}: {e}")

        schema_path = os.path.join(backup_subdir, "schema.sql")
        print(f"Exporting schema -> {schema_path}")
        export_schema(conn, schema_path)
    finally:
        conn.close()

    # Create zip file
    os.makedirs(out_dir, exist_ok=True)
    zip_name = os.path.join(out_dir, f"db_backup_{date_str}.zip")
    print(f"Creating zip -> {zip_name}")
    make_zip(backup_subdir, zip_name)

    # Remove unzipped folder
    try:
        shutil.rmtree(backup_subdir)
    except OSError:
        print(f"Warning: failed to remove temp folder {backup_subdir}")

    # Prune old backups
    prune_old_backups(out_dir, keep_days)

    print(f"Backup completed: {zip_name}")
    return 0


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create CSV backups and a zip from a SQLite database")
    p.add_argument("--db", default=default_db_path(), help="Path to SQLite database file")
    p.add_argument("--out-dir", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups")), help="Directory to store backup zip files")
    p.add_argument("--keep-days", type=int, default=30, help="How many days of backups to keep (zero or negative disables pruning)")
    return p.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    args = parse_args(argv)
    return run_backup(args.db, args.out_dir, args.keep_days)


if __name__ == "__main__":
    raise SystemExit(main())
