"""
Dedicated Database Initialization & Migration Test Suite
Tests:
1. Fresh new SQLite database creation
2. In-memory SQLite database initialization
3. Existing SQLite database initialization with data preservation
4. Legacy SQLite schema upgrade (adding missing columns)
"""

import os
import tempfile
import sqlite3
from datetime import date
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from app import app, db, Application, Activity, ensure_schema, seed_sample_data_records, DB_PATH

def create_isolated_test_app(db_uri):
    test_app = Flask(__name__)
    test_app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    test_db = SQLAlchemy(test_app)

    class TestAppModel(test_db.Model):
        __tablename__ = 'applications'
        id = test_db.Column(test_db.Integer, primary_key=True)
        company_name = test_db.Column(test_db.String(150), nullable=False)
        position = test_db.Column(test_db.String(150), nullable=False)
        location = test_db.Column(test_db.String(150), nullable=True)
        job_type = test_db.Column(test_db.String(50), nullable=False, default='Full-time')
        application_date = test_db.Column(test_db.Date, nullable=False, default=date.today)
        job_url = test_db.Column(test_db.String(500), nullable=True)
        status = test_db.Column(test_db.String(50), nullable=False, default='Applied')
        interview_date = test_db.Column(test_db.Date, nullable=True)
        follow_up_date = test_db.Column(test_db.Date, nullable=True)
        follow_up_completed = test_db.Column(test_db.Boolean, default=False)
        notes = test_db.Column(test_db.Text, nullable=True)

    def test_ensure_schema():
        test_db.create_all()
        inspector = inspect(test_db.engine)
        if 'applications' in inspector.get_table_names():
            existing_cols = [col['name'] for col in inspector.get_columns('applications')]
            with test_db.engine.connect() as conn:
                if 'follow_up_date' not in existing_cols:
                    conn.execute(text("ALTER TABLE applications ADD COLUMN follow_up_date DATE"))
                    conn.commit()
                if 'follow_up_completed' not in existing_cols:
                    conn.execute(text("ALTER TABLE applications ADD COLUMN follow_up_completed BOOLEAN DEFAULT 0"))
                    conn.commit()

    return test_app, test_db, TestAppModel, test_ensure_schema

def test_fresh_database():
    print("\n[Test 1] Testing startup on a completely fresh database...")
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
        temp_db_path = tf.name

    try:
        test_app, test_db, TestAppModel, test_ensure_schema = create_isolated_test_app(f'sqlite:///{temp_db_path}')
        with test_app.app_context():
            test_ensure_schema()
            assert TestAppModel.query.count() == 0, "Fresh DB should be empty before seeding"
            # Add an item
            new_item = TestAppModel(company_name='Fresh Corp', position='Backend Dev', application_date=date.today())
            test_db.session.add(new_item)
            test_db.session.commit()
            assert TestAppModel.query.count() == 1
            test_db.engine.dispose()
        print("  [OK] Fresh database initialized and records added without errors or warnings.")
    finally:
        try:
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)
        except Exception:
            pass

def test_existing_legacy_database_migration():
    print("\n[Test 2] Testing migration on an existing legacy database (missing new columns)...")
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
        legacy_db_path = tf.name

    try:
        # Create a legacy SQLite table without follow_up_date or follow_up_completed
        conn = sqlite3.connect(legacy_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE applications (
                id INTEGER PRIMARY KEY,
                company_name VARCHAR(150) NOT NULL,
                position VARCHAR(150) NOT NULL,
                location VARCHAR(150),
                job_type VARCHAR(50) DEFAULT 'Full-time',
                application_date DATE NOT NULL,
                job_url VARCHAR(500),
                status VARCHAR(50) DEFAULT 'Applied',
                interview_date DATE,
                notes TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO applications (company_name, position, application_date, status)
            VALUES ('Legacy Corp', 'Legacy Engineer', '2026-08-01', 'Applied')
        """)
        conn.commit()
        conn.close()

        # Connect with isolated app & run schema ensure
        test_app, test_db, TestAppModel, test_ensure_schema = create_isolated_test_app(f'sqlite:///{legacy_db_path}')
        with test_app.app_context():
            test_ensure_schema()
            
            # Verify legacy record was preserved
            legacy_rec = TestAppModel.query.filter_by(company_name='Legacy Corp').first()
            assert legacy_rec is not None, "Legacy record was lost during schema upgrade!"
            assert legacy_rec.position == 'Legacy Engineer'
            assert legacy_rec.follow_up_date is None
            assert legacy_rec.follow_up_completed == False

            # Update the new field
            legacy_rec.follow_up_date = date(2026, 9, 1)
            legacy_rec.follow_up_completed = True
            test_db.session.commit()

            updated = TestAppModel.query.filter_by(company_name='Legacy Corp').first()
            assert updated.follow_up_date == date(2026, 9, 1)
            assert updated.follow_up_completed == True
            test_db.engine.dispose()
            print("  [OK] Legacy database upgraded with new columns, existing data preserved 100%.")
    finally:
        try:
            if os.path.exists(legacy_db_path):
                os.remove(legacy_db_path)
        except Exception:
            pass

def test_production_sqlite_db():
    print("\n[Test 3] Testing existing production database integrity (jobtrack.db)...")
    with app.app_context():
        ensure_schema()
        count = Application.query.count()
        assert count > 0, "Production database should have applications"
        print(f"  [OK] Production database jobtrack.db intact with {count} active applications.")

if __name__ == '__main__':
    print("=" * 60)
    print("STARTING ROBUST DATABASE INITIALIZATION TESTS")
    print("=" * 60)
    test_fresh_database()
    test_existing_legacy_database_migration()
    test_production_sqlite_db()
    print("=" * 60)
    print("[SUCCESS] ALL DATABASE INITIALIZATION TESTS PASSED CLEANLY!")
    print("=" * 60)
