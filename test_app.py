import unittest
from datetime import date, timedelta
from app import app, db, Application, Activity, seed_sample_data_records, ensure_schema

class JobTrackTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()

        with app.app_context():
            db.create_all()
            ensure_schema()
            seed_sample_data_records()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_dashboard_loads_and_stats(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Good morning, Vignesh', response.data)
        self.assertIn(b'Total Applications', response.data)
        self.assertIn(b'Pipeline Breakdown', response.data)
        self.assertIn(b'Follow-ups Due', response.data)
        self.assertIn(b'Recent Activity', response.data)
        self.assertIn(b'Recent Applications', response.data)

    def test_pipeline_page(self):
        response = self.client.get('/pipeline')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Application Pipeline', response.data)
        self.assertIn(b'Saved', response.data)
        self.assertIn(b'Applied', response.data)
        self.assertIn(b'Screening', response.data)
        self.assertIn(b'Interview', response.data)
        self.assertIn(b'Offer', response.data)

    def test_find_jobs_and_apply_confirm(self):
        # 1. GET /jobs
        response = self.client.get('/jobs')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Find Job Opportunities', response.data)
        self.assertIn(b'Freshworks', response.data)

        # 2. Search /jobs
        res_search = self.client.get('/jobs?q=Python')
        self.assertEqual(res_search.status_code, 200)
        self.assertIn(b'Freshworks', res_search.data)

        # 3. POST /jobs/apply-confirm
        res_apply = self.client.post('/jobs/apply-confirm', data={
            'company_name': 'Atlassian Jira Team',
            'position': 'Senior Software Architect',
            'location': 'Bangalore',
            'job_type': 'Full-time',
            'job_url': 'https://atlassian.com/careers/123',
            'application_date': '2026-08-26',
            'follow_up_date': '2026-09-02',
            'notes': 'Applied for Jira Core backend role'
        }, follow_redirects=True)
        self.assertEqual(res_apply.status_code, 200)
        self.assertIn(b'Atlassian Jira Team', res_apply.data)

        # Verify Activity was logged
        with app.app_context():
            created_app = Application.query.filter_by(company_name='Atlassian Jira Team').first()
            self.assertIsNotNone(created_app)
            self.assertIsNotNone(created_app.follow_up_date)
            activities = Activity.query.filter_by(application_id=created_app.id).all()
            self.assertGreater(len(activities), 0)

    def test_mark_follow_up_done(self):
        with app.app_context():
            app_rec = Application.query.filter(Application.follow_up_date.isnot(None)).first()
            app_id = app_rec.id

        response = self.client.post(f'/applications/{app_id}/mark-follow-up-done', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'marked as completed', response.data)

        with app.app_context():
            updated = db.session.get(Application, app_id)
            self.assertTrue(updated.follow_up_completed)

    def test_quick_update_status(self):
        with app.app_context():
            app_rec = Application.query.filter_by(company_name='Freshworks').first()
            app_id = app_rec.id

        response = self.client.post(f'/applications/{app_id}/update-status', data={
            'status': 'Interview',
            'return_to': 'pipeline'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Updated Freshworks status to', response.data)

        with app.app_context():
            updated = db.session.get(Application, app_id)
            self.assertEqual(updated.status, 'Interview')

    def test_applications_list_and_search(self):
        response = self.client.get('/applications')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Job Applications', response.data)

        # Search
        res_search = self.client.get('/applications?q=Zoho')
        self.assertEqual(res_search.status_code, 200)
        self.assertIn(b'Zoho', res_search.data)
        self.assertNotIn(b'Infosys', res_search.data)

    def test_add_application_success_and_validation(self):
        # Validation error
        response = self.client.post('/applications/add', data={
            'company_name': '',
            'position': '',
            'application_date': '2026-08-26'
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Company name is required', response.data)

        # Success
        response = self.client.post('/applications/add', data={
            'company_name': 'Oracle',
            'position': 'Java Developer',
            'location': 'Bangalore',
            'job_type': 'Full-time',
            'application_date': '2026-08-26',
            'status': 'Applied',
            'job_url': 'https://oracle.com/careers',
            'follow_up_date': '2026-09-05',
            'notes': 'Submitted application'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Application added successfully', response.data)
        self.assertIn(b'Oracle', response.data)

    def test_application_details_and_activities(self):
        with app.app_context():
            app_record = Application.query.filter_by(company_name='Zoho').first()
            app_id = app_record.id

        response = self.client.get(f'/applications/{app_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Zoho', response.data)
        self.assertIn(b'Hiring Pipeline Progress', response.data)
        self.assertIn(b'Activity History', response.data)

    def test_edit_application(self):
        with app.app_context():
            app_record = Application.query.filter_by(company_name='TCS').first()
            app_id = app_record.id

        response = self.client.post(f'/applications/edit/{app_id}', data={
            'company_name': 'TCS Updated',
            'position': 'Senior Software Developer',
            'location': 'Chennai',
            'job_type': 'Full-time',
            'application_date': '2026-08-20',
            'status': 'Offer',
            'notes': 'Final offer confirmed'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Application updated successfully', response.data)

    def test_delete_application(self):
        with app.app_context():
            app_record = Application.query.filter_by(company_name='Wipro').first()
            app_id = app_record.id

        response = self.client.post(f'/applications/delete/{app_id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'deleted successfully', response.data)

        with app.app_context():
            deleted_app = db.session.get(Application, app_id)
            self.assertIsNone(deleted_app)

    def test_settings_page(self):
        response = self.client.get('/settings')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Settings & Preferences', response.data)
        self.assertIn(b'Theme & Appearance', response.data)

    def test_health_endpoint(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data.get('status'), 'ok')

    def test_title_consistency(self):
        for route in ['/', '/jobs', '/applications', '/pipeline', '/applications/add', '/settings']:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'<title>JobTrack \xe2\x80\x93 Job Application Tracker</title>', res.data)

if __name__ == '__main__':
    unittest.main()
