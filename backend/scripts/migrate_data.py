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


def generate_unique_username(base, cursor):
    """Generate a unique username by checking against existing usernames in the database"""
    base = (base or "").strip()
    if not base:
        base = "user"

    candidate = base
    suffix = 2

    while True:
        cursor.execute("SELECT 1 FROM users WHERE username = ? LIMIT 1", (candidate,))
        if not cursor.fetchone():
            break
        candidate = f"{base}#{suffix}"
        suffix += 1

    return candidate


def populate_username(dest_cursor):
    """Populate username field for users who don't have one using the same logic as Spotify route"""
    print("\nPopulating usernames for users without them...")

    # Check if users table exists
    dest_cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
    )
    if not dest_cursor.fetchone():
        print("  Users table not found, skipping username population")
        return

    # Find users without usernames
    dest_cursor.execute(
        "SELECT id, name, email FROM users WHERE username IS NULL OR username = ''"
    )
    users_without_username = dest_cursor.fetchall()

    if not users_without_username:
        print("  All users already have usernames")
        return

    print(f"  Found {len(users_without_username)} users without usernames")

    updated_count = 0
    for user_id, name, email in users_without_username:
        # Apply the same logic as in the Spotify route
        base_username = (
            (name or "").strip() or (email or "").split("@")[0]
            if email
            else "" or user_id
        )

        unique_username = generate_unique_username(base_username, dest_cursor)

        # Update the user with the new username
        dest_cursor.execute(
            "UPDATE users SET username = ? WHERE id = ?", (unique_username, user_id)
        )
        updated_count += 1
        print(f"    Updated user {user_id} with username: {unique_username}")

    print(f"  Successfully populated usernames for {updated_count} users")


def deduplicate_plays(dest_cursor):
    """Remove duplicate records from plays table based on user_id, track_id and date"""
    print("\nDeduplicating plays table...")

    # First, check if plays table exists
    dest_cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='plays'"
    )
    if not dest_cursor.fetchone():
        print("  Plays table not found, skipping deduplication")
        return

    # Count total records before deduplication
    dest_cursor.execute("SELECT COUNT(*) FROM plays")
    total_before = dest_cursor.fetchone()[0]
    print(f"  Total plays before deduplication: {total_before}")

    # Find duplicates based on user_id, track_id, and date (treating datetime variations as same)
    # We'll keep the record with the minimum rowid (oldest record) for each group
    dedup_query = """
        DELETE FROM plays
        WHERE rowid NOT IN (
            SELECT MIN(rowid)
            FROM plays
            GROUP BY user_id, track_id, DATE(date)
        )
    """

    dest_cursor.execute(dedup_query)
    deleted_count = dest_cursor.rowcount

    # Count records after deduplication
    dest_cursor.execute("SELECT COUNT(*) FROM plays")
    total_after = dest_cursor.fetchone()[0]

    print(f"  Deleted {deleted_count} duplicate records")
    print(f"  Total plays after deduplication: {total_after}")


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

        # Populate usernames for users without them
        populate_username(dest_cursor)

        # Deduplicate plays after migration
        deduplicate_plays(dest_cursor)

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
