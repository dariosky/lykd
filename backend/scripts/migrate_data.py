#!/usr/bin/env python3
"""
Script to migrate data from spotlike.sqlite to lykd.sqlite
Handles table name changes: album_artist -> albumartist, track_artist -> trackartist
"""

import sqlite3
import sys

import settings


def get_table_columns(cursor, table_name):
    """Get column names for a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def copy_table_data(source_cursor, dest_cursor, source_table, dest_table):
    """Copy data from source table to destination table with upsert"""
    print(f"Copying data from {source_table} to {dest_table}...")

    # Get columns from both tables
    source_columns = get_table_columns(source_cursor, source_table)
    dest_columns = get_table_columns(dest_cursor, dest_table)

    # Use common columns
    common_columns = [col for col in source_columns if col in dest_columns]
    columns_str = ", ".join(common_columns)
    placeholders = ", ".join(["?" for _ in common_columns])

    print(f"  Common columns: {common_columns}")

    # Get all data from source table
    source_cursor.execute(f"SELECT {columns_str} FROM {source_table}")  # nosec B608
    rows = source_cursor.fetchall()

    if not rows:
        print(f"  No data found in {source_table}")
        return

    # Create upsert query for destination table
    # For SQLite, we use INSERT OR REPLACE
    upsert_query = f"""
        INSERT OR REPLACE INTO {dest_table} ({columns_str})
        VALUES ({placeholders})
    """

    # Insert data
    dest_cursor.executemany(upsert_query, rows)
    rows_affected = dest_cursor.rowcount
    print(f"  Copied {len(rows)} rows to {dest_table} (affected: {rows_affected})")


def main():
    script_dir = settings.BACKEND_DIR
    source_db = script_dir / "spotlike.sqlite"
    dest_db = script_dir / "lykd.sqlite"

    if not source_db.exists():
        print(f"Error: Source database {source_db} not found!")
        sys.exit(1)

    if not dest_db.exists():
        print(f"Error: Destination database {dest_db} not found!")
        print("Make sure to run alembic migrations first to create the tables.")
        sys.exit(1)

    print(f"Migrating data from {source_db} to {dest_db}")

    # Connect to both databases
    source_conn = sqlite3.connect(source_db)
    dest_conn = sqlite3.connect(dest_db)

    try:
        source_cursor = source_conn.cursor()
        dest_cursor = dest_conn.cursor()

        # Get list of tables from source database
        source_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != 'alembic_version'"
        )
        source_tables = [row[0] for row in source_cursor.fetchall()]

        # Get list of tables from destination database
        dest_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != 'alembic_version'"
        )
        dest_tables = [row[0] for row in dest_cursor.fetchall()]

        print(f"Source tables: {source_tables}")
        print(f"Destination tables: {dest_tables}")
        print()

        # Define table mappings (source -> destination)
        table_mappings = {
            "user": "users",
            "artist": "artists",
            "album": "albums",
            "track": "tracks",
            "albumartist": "albums_artists",  # Source has albumartist
            "trackartist": "artists_tracks",  # Source has trackartist
            "play": "plays",
            "liked": "likes",
        }

        # Copy data for each table mapping
        for source_table, dest_table in table_mappings.items():
            if source_table in source_tables and dest_table in dest_tables:
                copy_table_data(source_cursor, dest_cursor, source_table, dest_table)
            elif source_table in source_tables:
                print(
                    f"Warning: Source table '{source_table}' exists but destination table '{dest_table}' not found"
                )
            # Skip if source table doesn't exist (it's expected for some mappings)

        # Commit all changes
        dest_conn.commit()
        print("\nData migration completed successfully!")

        # Show summary
        print("\nSummary:")
        for dest_table in dest_tables:
            if dest_table != "alembic_version":
                dest_cursor.execute(f"SELECT COUNT(*) FROM {dest_table}")  # nosec B608:hardcoded_sql_expressions
                count = dest_cursor.fetchone()[0]
                print(f"  {dest_table}: {count} rows")

    except Exception as e:
        print(f"Error during migration: {e}")
        dest_conn.rollback()
        sys.exit(1)

    finally:
        source_conn.close()
        dest_conn.close()


if __name__ == "__main__":
    main()
