"""
JobTrack - SQLite to PostgreSQL Data Migration Utility

Copies existing application and activity data from local SQLite database (database/jobtrack.db)
to a PostgreSQL database specified in the DATABASE_URL environment variable.

Features:
- Preserves primary keys (IDs), timestamps, notes, and activity history
- Idempotent: skips existing records to prevent duplicates on rerun
- Updates PostgreSQL auto-increment sequences after explicit ID inserts
- Safe transaction handling (commits on success, rolls back on error)
- Never modifies or deletes the original SQLite database
- Never prints passwords or raw database connection credentials
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text, Table, MetaData
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SQLITE_DB_PATH = os.path.join(BASE_DIR, 'database', 'jobtrack.db')


def mask_db_url(url_str):
    """Mask credentials in database URL for safe logging."""
    if not url_str:
        return "<none>"
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url_str)
        masked_netloc = parsed.netloc
        if parsed.password:
            masked_netloc = masked_netloc.replace(f":{parsed.password}@", ":***@")
        return f"{parsed.scheme}://{masked_netloc}{parsed.path}"
    except Exception:
        return "postgresql://***:***@<masked-host>/<masked-db>"


def run_migration():
    print("=" * 65)
    print(" JobTrack - SQLite to PostgreSQL Data Migration")
    print("=" * 65)

    # 1. Verify SQLite source database
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"[ERROR] Local SQLite database not found at: {SQLITE_DB_PATH}")
        print("Please ensure the database file exists before migrating.")
        sys.exit(1)

    # 2. Verify target DATABASE_URL
    target_url = os.getenv('DATABASE_URL')
    if not target_url or not target_url.strip():
        print("[ERROR] DATABASE_URL environment variable is not set.")
        print("Please set DATABASE_URL (e.g., Render PostgreSQL connection string) and run again.")
        sys.exit(1)

    target_url = target_url.strip()
    if target_url.startswith('postgres://'):
        target_url = target_url.replace('postgres://', 'postgresql://', 1)

    if target_url.startswith('sqlite'):
        print("[ERROR] DATABASE_URL is pointing to a SQLite database.")
        print("This migration tool is intended for migrating to PostgreSQL.")
        sys.exit(1)

    masked_target = mask_db_url(target_url)
    print(f"\n[Source] SQLite database: {SQLITE_DB_PATH}")
    print(f"[Target] PostgreSQL database: {masked_target}")

    # 3. Create SQLAlchemy engines
    sqlite_engine = create_engine(f"sqlite:///{SQLITE_DB_PATH}")
    pg_engine = create_engine(target_url)

    # 4. Ensure tables exist in target PostgreSQL database
    print("\n[1/4] Ensuring tables exist in target PostgreSQL database...")
    try:
        from app import app, db
        with app.app_context():
            # Import models and create tables
            db.metadata.create_all(bind=pg_engine)
        print("  [OK] Target database tables verified/created.")
    except Exception as e:
        print(f"[ERROR] Failed to connect or create tables on target database: {e}")
        sys.exit(1)

    # 5. Read data from SQLite
    print("\n[2/4] Reading existing data from local SQLite database...")
    sqlite_inspector = inspect(sqlite_engine)
    sqlite_tables = sqlite_inspector.get_table_names()

    if 'applications' not in sqlite_tables:
        print("[INFO] No 'applications' table found in SQLite database. Nothing to migrate.")
        return

    sqlite_metadata = MetaData()
    sqlite_apps_table = Table('applications', sqlite_metadata, autoload_with=sqlite_engine)
    sqlite_activities_table = Table('activities', sqlite_metadata, autoload_with=sqlite_engine) if 'activities' in sqlite_tables else None

    with sqlite_engine.connect() as sqlite_conn:
        sqlite_apps = sqlite_conn.execute(sqlite_apps_table.select()).mappings().all()
        sqlite_activities = sqlite_conn.execute(sqlite_activities_table.select()).mappings().all() if sqlite_activities_table is not None else []

    print(f"  Found {len(sqlite_apps)} application record(s) in SQLite.")
    print(f"  Found {len(sqlite_activities)} activity record(s) in SQLite.")

    if not sqlite_apps and not sqlite_activities:
        print("[INFO] No records found in SQLite. Migration complete (0 records).")
        return

    # 6. Migrate to PostgreSQL
    print("\n[3/4] Copying records to PostgreSQL (preserving IDs)...")
    pg_metadata = MetaData()
    pg_apps_table = Table('applications', pg_metadata, autoload_with=pg_engine)
    pg_activities_table = Table('activities', pg_metadata, autoload_with=pg_engine)

    apps_inserted = 0
    apps_skipped = 0
    activities_inserted = 0
    activities_skipped = 0

    try:
        with pg_engine.begin() as pg_conn:
            # Check existing IDs in PostgreSQL to avoid duplicates
            existing_app_ids = {row[0] for row in pg_conn.execute(text("SELECT id FROM applications")).fetchall()}
            existing_activity_ids = {row[0] for row in pg_conn.execute(text("SELECT id FROM activities")).fetchall()}

            # Migrate Applications
            for row in sqlite_apps:
                row_dict = dict(row)
                app_id = row_dict.get('id')

                if app_id in existing_app_ids:
                    apps_skipped += 1
                    continue

                # Ensure defaults for boolean fields if missing in legacy records
                if 'follow_up_completed' not in row_dict or row_dict['follow_up_completed'] is None:
                    row_dict['follow_up_completed'] = False
                else:
                    row_dict['follow_up_completed'] = bool(row_dict['follow_up_completed'])

                pg_conn.execute(pg_apps_table.insert().values(**row_dict))
                apps_inserted += 1

            # Migrate Activities
            for row in sqlite_activities:
                row_dict = dict(row)
                act_id = row_dict.get('id')

                if act_id in existing_activity_ids:
                    activities_skipped += 1
                    continue

                pg_conn.execute(pg_activities_table.insert().values(**row_dict))
                activities_inserted += 1

            # 7. Update PostgreSQL sequences for auto-increment IDs
            print("\n[4/4] Synchronizing PostgreSQL auto-increment sequences...")
            if pg_engine.url.drivername.startswith('postgresql'):
                try:
                    pg_conn.execute(text("""
                        SELECT setval(
                            pg_get_serial_sequence('applications', 'id'),
                            COALESCE((SELECT MAX(id) FROM applications), 1),
                            (SELECT MAX(id) IS NOT NULL FROM applications)
                        );
                    """))
                    pg_conn.execute(text("""
                        SELECT setval(
                            pg_get_serial_sequence('activities', 'id'),
                            COALESCE((SELECT MAX(id) FROM activities), 1),
                            (SELECT MAX(id) IS NOT NULL FROM activities)
                        );
                    """))
                    print("  [OK] PostgreSQL sequences updated successfully.")
                except Exception as seq_err:
                    print(f"  [Notice] Sequence synchronization note: {seq_err}")

        print("\n" + "=" * 65)
        print(" [SUCCESS] MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 65)
        print(f" Applications: {apps_inserted} inserted, {apps_skipped} already existed.")
        print(f" Activities  : {activities_inserted} inserted, {activities_skipped} already existed.")
        print(" Original SQLite database remains 100% intact and unchanged.")
        print("=" * 65)

    except Exception as err:
        print(f"\n[ERROR] Migration failed and was rolled back: {err}")
        sys.exit(1)


if __name__ == '__main__':
    run_migration()
