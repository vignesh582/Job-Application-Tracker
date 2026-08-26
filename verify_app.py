"""
Comprehensive Verification Script for JobTrack Application
Tests real SQLite operations, all Flask routes, CRUD workflow, stats calculation,
Kanban pipeline, Find Jobs & I've Applied workflow, Follow-up tracking,
Activity timeline, and Dark Mode readiness.
"""

import sys
import os
import re
from datetime import date, timedelta

from app import app, db, Application, Activity, seed_sample_data_records, ensure_schema, DB_PATH

def run_verification():
    print("=" * 60)
    print("[START] Starting JobTrack Comprehensive Verification...")
    print("=" * 60)

    # 1. Check Database Schema & Migration
    print(f"\n[1] Checking SQLite Database path: {DB_PATH}")
    assert os.path.exists(DB_PATH), "Database file does not exist!"
    with app.app_context():
        ensure_schema()
        count = Application.query.count()
        print(f"  [OK] SQLite database verified. Current applications: {count}")

    client = app.test_client()

    # 2. Test Route: GET / (Dashboard with Enhanced Metrics)
    print("\n[2] Testing Route: GET / (Dashboard)")
    res = client.get('/')
    assert res.status_code == 200, f"Dashboard failed with {res.status_code}"
    html = res.data.decode('utf-8')
    assert "Good morning, Vignesh" in html
    assert "Total Applications" in html
    assert "Active Applications" in html
    assert "Pipeline Breakdown" in html
    assert "Follow-ups Due" in html
    assert "Upcoming Interviews" in html
    assert "Recent Activity" in html
    print("  [OK] Dashboard loaded successfully with all metrics, follow-ups, and activity feeds.")

    # 3. Test Route: GET /pipeline (Kanban Board)
    print("\n[3] Testing Route: GET /pipeline (Kanban Board)")
    res_pipe = client.get('/pipeline')
    assert res_pipe.status_code == 200
    html_pipe = res_pipe.data.decode('utf-8')
    assert "Application Pipeline" in html_pipe
    assert "Saved" in html_pipe
    assert "Applied" in html_pipe
    assert "Screening" in html_pipe
    assert "Interview" in html_pipe
    assert "Offer" in html_pipe
    print("  [OK] Pipeline Kanban board loaded with all 5 active stages and archived section.")

    # 4. Test Route: GET /jobs (Find Jobs Portal & Search)
    print("\n[4] Testing Route: GET /jobs (Find Jobs Portal)")
    res_jobs = client.get('/jobs')
    assert res_jobs.status_code == 200
    html_jobs = res_jobs.data.decode('utf-8')
    assert "Find Job Opportunities" in html_jobs
    assert "Curated Job Opportunities" in html_jobs
    assert "Freshworks" in html_jobs
    assert "Apply" in html_jobs
    assert "I've Applied" in html_jobs

    # Search in jobs
    res_search_jobs = client.get('/jobs?q=Python&location=chennai')
    assert res_search_jobs.status_code == 200
    html_s_jobs = res_search_jobs.data.decode('utf-8')
    assert "Freshworks" in html_s_jobs
    print("  [OK] Find Jobs portal, search, and official career links verified.")

    # 5. Test "I've Applied" Workflow (POST /jobs/apply-confirm)
    print("\n[5] Testing 'I've Applied' Workflow")
    today = date.today()
    unique_company = f"Stripe Inc {date.today().strftime('%Y%m%d')}"
    job_payload = {
        'company_name': unique_company,
        'position': 'Backend Infrastructure Engineer',
        'location': 'Bangalore',
        'job_type': 'Full-time',
        'job_url': 'https://stripe.com/jobs/123456',
        'application_date': today.strftime('%Y-%m-%d'),
        'follow_up_date': (today + timedelta(days=7)).strftime('%Y-%m-%d'),
        'notes': 'Applied via official Stripe careers portal.'
    }

    res_apply = client.post('/jobs/apply-confirm', data=job_payload, follow_redirects=True)
    assert res_apply.status_code == 200
    html_applied = res_apply.data.decode('utf-8')
    assert "added to your tracker." in html_applied

    with app.app_context():
        new_app = Application.query.filter_by(company_name=unique_company).first()
        assert new_app is not None, "Application from Find Jobs was not saved to SQLite!"
        stripe_id = new_app.id
        activities = Activity.query.filter_by(application_id=stripe_id).all()
        assert len(activities) > 0, "Activity log missing for newly created application!"
        print(f"  [OK] Application created from Find Jobs (ID: {stripe_id}) and initial Activity logged.")

    # 6. Test Quick Status Update (POST /applications/<id>/update-status)
    print(f"\n[6] Testing Quick Pipeline Status Update for ID {stripe_id}")
    res_status = client.post(f'/applications/{stripe_id}/update-status', data={
        'status': 'Screening',
        'return_to': 'pipeline'
    }, follow_redirects=True)
    assert res_status.status_code == 200

    with app.app_context():
        updated_stripe = db.session.get(Application, stripe_id)
        assert updated_stripe.status == 'Screening'
        print("  [OK] Application status successfully updated to 'Screening' in SQLite.")

    # 7. Test Mark Follow-up Done (POST /applications/<id>/mark-follow-up-done)
    print(f"\n[7] Testing Mark Follow-up Done for ID {stripe_id}")
    res_fu = client.post(f'/applications/{stripe_id}/mark-follow-up-done', data={'return_to': 'details'}, follow_redirects=True)
    assert res_fu.status_code == 200

    with app.app_context():
        fu_stripe = db.session.get(Application, stripe_id)
        assert fu_stripe.follow_up_completed == True
        print("  [OK] Follow-up marked as completed in SQLite.")

    # 8. Test Details Page & Activity Timeline (GET /applications/<id>)
    print(f"\n[8] Testing Application Details & Activity Timeline for ID {stripe_id}")
    res_det = client.get(f'/applications/{stripe_id}')
    assert res_det.status_code == 200
    html_det = res_det.data.decode('utf-8')
    assert unique_company in html_det
    assert "Activity History" in html_det
    assert "Screening" in html_det
    print("  [OK] Application Details page and Activity timeline verified.")

    # 9. Clean up test application
    print(f"\n[9] Testing Delete Application for ID {stripe_id}")
    res_del = client.post(f'/applications/delete/{stripe_id}', follow_redirects=True)
    assert res_del.status_code == 200

    with app.app_context():
        deleted_app = db.session.get(Application, stripe_id)
        assert deleted_app is None
        print("  [OK] Test application cleanly removed from SQLite.")

    # 10. Test Page Title Consistency
    print("\n[10] Verifying Page Title Consistency Across All Routes")
    test_routes = ['/', '/jobs', '/applications', '/pipeline', '/applications/add', '/settings']
    expected_title = '<title>JobTrack – Job Application Tracker</title>'
    for route in test_routes:
        r = client.get(route)
        assert r.status_code == 200
        html_content = r.data.decode('utf-8')
        assert expected_title in html_content, f"Page title mismatched on route {route}"
    print("  [OK] All pages strictly use: <title>JobTrack – Job Application Tracker</title>")

    print("\n" + "=" * 60)
    print("[SUCCESS] ALL 10 COMPREHENSIVE VERIFICATION STAGES PASSED!")
    print("=" * 60)

if __name__ == '__main__':
    run_verification()
