#!/usr/bin/env python3
"""
Script to migrate data from spotlike.sqlite to lykd.sqlite
Handles table name changes: album_artist -> albumartist, track_artist -> trackartist
Uses SQLModel throughout to avoid database locking issues.
"""

import sys
from typing import Any, Dict, List

import settings
from models.auth import User, populate_username
from sqlmodel import Session, create_engine, select, text


def get_table_info_sqlmodel(session: Session, table_name: str) -> List[Dict[str, Any]]:
    """Get table info using SQLModel session"""
    result = session.exec(text(f"PRAGMA table_info({table_name})"))
    return [
        {
            "cid": row[0],
            "name": row[1],
            "type": row[2],
            "notnull": row[3],
            "dflt_value": row[4],
            "pk": row[5],
        }
        for row in result.fetchall()
    ]


def get_table_columns_sqlmodel(session: Session, table_name: str) -> List[str]:
    """Get column names for a table using SQLModel session"""
    table_info = get_table_info_sqlmodel(session, table_name)
    return [col["name"] for col in table_info]


def copy_table_data_sqlmodel(
    source_session: Session, dest_session: Session, source_table: str, dest_table: str
):
    """Copy data from source table to destination table using SQLModel"""
    print(f"Copying data from {source_table} to {dest_table}...")

    # Get columns from both tables
    source_columns = get_table_columns_sqlmodel(source_session, source_table)
    dest_columns = get_table_columns_sqlmodel(dest_session, dest_table)

    # Use common columns
    common_columns = [col for col in source_columns if col in dest_columns]
    columns_str = ", ".join(common_columns)

    print(f"  Common columns: {common_columns}")

    if not common_columns:
        print(f"  No common columns found between {source_table} and {dest_table}")
        return

    # Get all data from source table
    source_query = text(f"SELECT {columns_str} FROM {source_table}")  # nosec B608
    result = source_session.exec(source_query)
    rows = result.fetchall()

    if not rows:
        print(f"  No data found in {source_table}")
        return

    # Insert data into destination table
    placeholders = ", ".join([f":{col}" for col in common_columns])
    insert_query = (
        f"INSERT OR REPLACE INTO {dest_table} ({columns_str}) VALUES ({placeholders})"
    )

    # Use session.execute() with raw SQL and parameters
    for row in rows:
        # Convert row to dictionary with column names as keys
        row_dict = {}
        for i, col in enumerate(common_columns):
            row_dict[col] = row[i] if i < len(row) else None
        dest_session.execute(text(insert_query), row_dict)

    dest_session.commit()
    print(f"  Copied {len(rows)} rows to {dest_table}")


def populate_usernames_sqlmodel(dest_session: Session):
    """Populate username field for users who don't have one using the auth model function"""
    print("\nPopulating usernames for users without them...")

    # Find users without usernames
    users_without_username = dest_session.exec(
        select(User).where((User.username.is_(None)) | (User.username == ""))
    ).all()

    if not users_without_username:
        print("  All users already have usernames")
        return

    print(f"  Found {len(users_without_username)} users without usernames")

    updated_count = 0
    for user in users_without_username:
        # Use the populate_username function from models.auth
        username = populate_username(dest_session, user)
        updated_count += 1
        print(f"    Updated user {user.id} with username: {username}")
    dest_session.commit()

    print(f"  Successfully populated usernames for {updated_count} users")


def deduplicate_plays_sqlmodel(dest_session: Session):
    """Remove duplicate records from plays table based on user_id, track_id and date"""
    print("\nDeduplicating plays table...")

    # Check if plays table exists by trying to query it
    try:
        count_query = text("SELECT COUNT(*) FROM plays")
        result = dest_session.exec(count_query)
        total_before = result.fetchone()[0]
        print(f"  Total plays before deduplication: {total_before}")
    except Exception:
        print("  Plays table not found, skipping deduplication")
        return

    # Find duplicates based on user_id, track_id, and date (treating datetime variations as same)
    # We'll keep the record with the minimum rowid (oldest record) for each group
    dedup_query = text("""
        DELETE FROM plays
        WHERE rowid NOT IN (
            SELECT MIN(rowid)
            FROM plays
            GROUP BY user_id, track_id, DATE(date)
        )
    """)

    result = dest_session.exec(dedup_query)
    dest_session.commit()

    # Count records after deduplication
    count_after_result = dest_session.exec(count_query)
    total_after = count_after_result.fetchone()[0]

    deleted_count = total_before - total_after
    print(f"  Deleted {deleted_count} duplicate records")
    print(f"  Total plays after deduplication: {total_after}")


def get_tables_list(session: Session) -> List[str]:
    """Get list of tables from database using SQLModel session"""
    query = text("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%' 
        AND name != 'alembic_version'
    """)
    result = session.exec(query)
    return [row[0] for row in result.fetchall()]


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

    # Create SQLModel engines and sessions
    source_engine = create_engine(f"sqlite:///{source_db}")
    dest_engine = create_engine(f"sqlite:///{dest_db}")

    try:
        with (
            Session(source_engine) as source_session,
            Session(dest_engine) as dest_session,
        ):
            # Get list of tables from both databases
            source_tables = get_tables_list(source_session)
            dest_tables = get_tables_list(dest_session)

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
                    copy_table_data_sqlmodel(
                        source_session, dest_session, source_table, dest_table
                    )
                elif source_table in source_tables:
                    print(
                        f"Warning: Source table '{source_table}' exists but destination table '{dest_table}' not found"
                    )
                # Skip if source table doesn't exist (it's expected for some mappings)

            # Populate usernames for users without them
            populate_usernames_sqlmodel(dest_session)

            # Deduplicate plays after migration
            deduplicate_plays_sqlmodel(dest_session)

            print("\nData migration completed successfully!")

            # Show summary
            print("\nSummary:")
            for dest_table in dest_tables:
                if dest_table != "alembic_version":
                    count_query = text(f"SELECT COUNT(*) FROM {dest_table}")  # nosec B608
                    result = dest_session.exec(count_query)
                    count = result.fetchone()[0]
                    print(f"  {dest_table}: {count} rows")

    except Exception as e:
        print(f"Error during migration: {e}")
        print(e.with_traceback())
        sys.exit(1)


if __name__ == "__main__":  # pragma no cover
    main()
