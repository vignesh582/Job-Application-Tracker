import os
import re
import sqlite3
from datetime import datetime, date, timedelta, timezone
from urllib.parse import urlparse

from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory & DB setup
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_DIR = os.path.join(BASE_DIR, 'database')
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, 'jobtrack.db')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'jobtrack-super-secret-production-key-2026')

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Allowed constants & Status Workflow
VALID_STATUSES = ['Saved', 'Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn']
VALID_JOB_TYPES = ['Full-time', 'Part-time', 'Internship', 'Contract']


# ==========================================
# DATABASE MODELS
# ==========================================

class Application(db.Model):
    __tablename__ = 'applications'

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    position = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(150), nullable=True)
    job_type = db.Column(db.String(50), nullable=False, default='Full-time')
    application_date = db.Column(db.Date, nullable=False, default=date.today)
    job_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(50), nullable=False, default='Applied')
    interview_date = db.Column(db.Date, nullable=True)
    follow_up_date = db.Column(db.Date, nullable=True)
    follow_up_completed = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship to activities
    activities = db.relationship('Activity', backref='application', cascade='all, delete-orphan', order_by='Activity.created_at.desc()')

    def __repr__(self):
        return f'<Application {self.id}: {self.company_name} - {self.position}>'

    def to_dict(self):
        return {
            'id': self.id,
            'company_name': self.company_name,
            'position': self.position,
            'location': self.location,
            'job_type': self.job_type,
            'application_date': self.application_date.isoformat() if self.application_date else None,
            'job_url': self.job_url,
            'status': self.status,
            'interview_date': self.interview_date.isoformat() if self.interview_date else None,
            'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None,
            'follow_up_completed': self.follow_up_completed,
            'notes': self.notes,
        }


class Activity(db.Model):
    __tablename__ = 'activities'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # 'created', 'status_change', 'interview_scheduled', 'follow_up_done', 'note_updated'
    description = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Activity {self.id} for App {self.application_id}: {self.description}>'


# ==========================================
# CURATED SAMPLE JOBS FOR "FIND JOBS"
# ==========================================

SAMPLE_JOBS_LISTINGS = [
    {
        'id': 'job-freshworks-01',
        'company_name': 'Freshworks',
        'position': 'Backend Engineer (Python / Django)',
        'location': 'Chennai',
        'job_type': 'Full-time',
        'experience_level': 'Mid-Senior (2-5 yrs)',
        'department': 'Core Platform Engineering',
        'salary_range': '₹16,00,000 – ₹24,00,000 / yr',
        'description': 'Join the core platform team to build high-scale distributed backend services, asynchronous workers, and RESTful APIs using Python, PostgreSQL, and AWS.',
        'skills': ['Python', 'Django', 'PostgreSQL', 'AWS', 'REST APIs', 'Docker'],
        'official_url': 'https://www.freshworks.com/careers/',
        'posted_time': '2 days ago'
    },
    {
        'id': 'job-zoho-02',
        'company_name': 'Zoho',
        'position': 'Software Development Engineer',
        'location': 'Chennai',
        'job_type': 'Full-time',
        'experience_level': 'Entry – Mid (0-3 yrs)',
        'department': 'SaaS Applications Group',
        'salary_range': '₹8,00,000 – ₹15,00,000 / yr',
        'description': 'Architect scalable SaaS enterprise tools. Responsible for writing clean, optimized algorithms, database queries, and modular frontend components.',
        'skills': ['Java', 'C++', 'Data Structures', 'Algorithms', 'SQL', 'JavaScript'],
        'official_url': 'https://www.zoho.com/careers/',
        'posted_time': '1 day ago'
    },
    {
        'id': 'job-google-03',
        'company_name': 'Google',
        'position': 'Software Engineer III (Cloud Infra)',
        'location': 'Bangalore',
        'job_type': 'Full-time',
        'experience_level': 'Senior (4+ yrs)',
        'department': 'Google Cloud Platform',
        'salary_range': 'Competitive / Top of Market',
        'description': 'Design, develop, test, deploy, maintain and improve large-scale distributed systems powering Google Cloud storage and compute services.',
        'skills': ['Go', 'C++', 'Distributed Systems', 'Kubernetes', 'gRPC'],
        'official_url': 'https://careers.google.com/',
        'posted_time': '3 days ago'
    },
    {
        'id': 'job-amazon-04',
        'company_name': 'Amazon',
        'position': 'Software Development Engineer I (SDE 1)',
        'location': 'Hyderabad',
        'job_type': 'Full-time',
        'experience_level': 'Entry (0-2 yrs)',
        'department': 'Amazon Web Services (AWS)',
        'salary_range': '₹18,00,000 – ₹26,00,000 / yr',
        'description': 'Work on world-class cloud infrastructure and customer-facing e-commerce systems. Participate in architectural reviews and agile deployments.',
        'skills': ['Java', 'Python', 'AWS Services', 'Object-Oriented Design', 'NoSQL'],
        'official_url': 'https://www.amazon.jobs/',
        'posted_time': 'Just now'
    },
    {
        'id': 'job-microsoft-05',
        'company_name': 'Microsoft',
        'position': 'Full Stack Developer',
        'location': 'Hyderabad',
        'job_type': 'Full-time',
        'experience_level': 'Mid (2-4 yrs)',
        'department': 'Azure Developer Experience',
        'salary_range': '₹20,00,000 – ₹30,00,000 / yr',
        'description': 'Build intuitive and highly performant developer portal interfaces and backend orchestration services for Azure cloud developers worldwide.',
        'skills': ['TypeScript', 'React', 'C#', '.NET Core', 'Azure', 'GraphQL'],
        'official_url': 'https://careers.microsoft.com/',
        'posted_time': '4 days ago'
    },
    {
        'id': 'job-tcs-06',
        'company_name': 'TCS',
        'position': 'Python & Data Analytics Specialist',
        'location': 'Chennai',
        'job_type': 'Full-time',
        'experience_level': 'Mid (2-5 yrs)',
        'department': 'Cognitive Business Operations',
        'salary_range': '₹7,50,000 – ₹12,00,000 / yr',
        'description': 'Develop automated data validation pipelines, ETL workflows, and statistical analytical models for international banking clients.',
        'skills': ['Python', 'Pandas', 'SQL', 'Tableau', 'ETL', 'Machine Learning'],
        'official_url': 'https://www.tcs.com/careers/',
        'posted_time': '5 days ago'
    },
    {
        'id': 'job-infosys-07',
        'company_name': 'Infosys',
        'position': 'Cloud Application Developer',
        'location': 'Bangalore',
        'job_type': 'Full-time',
        'experience_level': 'Entry-Mid (1-3 yrs)',
        'department': 'Infosys Cobalt Cloud',
        'salary_range': '₹6,50,000 – ₹10,50,000 / yr',
        'description': 'Migrate monolithic legacy architectures into cloud-native microservices with Docker, Spring Boot, and CI/CD automated deployment pipelines.',
        'skills': ['Spring Boot', 'Java', 'Docker', 'Jenkins', 'REST APIs'],
        'official_url': 'https://www.infosys.com/careers/',
        'posted_time': '3 days ago'
    },
    {
        'id': 'job-wipro-08',
        'company_name': 'Wipro',
        'position': 'Associate QA Automation Engineer',
        'location': 'Hyderabad',
        'job_type': 'Full-time',
        'experience_level': 'Entry (1-2 yrs)',
        'department': 'Enterprise Quality Engineering',
        'salary_range': '₹5,00,000 – ₹8,50,000 / yr',
        'description': 'Implement end-to-end automated UI and API test suites using Selenium WebDriver, PyTest, and Postman to ensure flawless software releases.',
        'skills': ['Selenium', 'Python', 'PyTest', 'Postman', 'Git', 'Jira'],
        'official_url': 'https://careers.wipro.com/',
        'posted_time': '6 days ago'
    },
    {
        'id': 'job-atlassian-09',
        'company_name': 'Atlassian',
        'position': 'Frontend Engineer (Jira Cloud)',
        'location': 'Bangalore',
        'job_type': 'Full-time',
        'experience_level': 'Mid (2-5 yrs)',
        'department': 'Product Engineering',
        'salary_range': '₹24,00,000 – ₹36,00,000 / yr',
        'description': 'Craft fluid, accessible, and high-performance user interfaces for Jira Cloud used daily by tens of millions of software development teams.',
        'skills': ['JavaScript', 'React', 'Redux', 'CSS3', 'Web Accessibility', 'Jest'],
        'official_url': 'https://www.atlassian.com/company/careers/',
        'posted_time': '2 days ago'
    },
    {
        'id': 'job-cognizant-10',
        'company_name': 'Cognizant',
        'position': 'Software Engineering Intern',
        'location': 'Coimbatore',
        'job_type': 'Internship',
        'experience_level': 'Student / Intern',
        'department': 'Digital Engineering Campus Batch',
        'salary_range': '₹25,000 / month stipend',
        'description': 'Hands-on 6-month internship training covering modern web stacks, cloud fundamentals, collaborative version control, and live customer projects.',
        'skills': ['Python', 'HTML/CSS', 'JavaScript', 'SQL', 'Git'],
        'official_url': 'https://careers.cognizant.com/',
        'posted_time': '1 day ago'
    }
]


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def log_activity(application_id, activity_type, description):
    """Safely logs an activity event for an application."""
    try:
        activity = Activity(
            application_id=application_id,
            activity_type=activity_type,
            description=description,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(activity)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[Activity Log Warning] Failed to log activity: {e}")


def validate_url(url_string):
    """Validates if the provided string is a valid web URL."""
    if not url_string:
        return True
    url_string = url_string.strip()
    try:
        result = urlparse(url_string)
        if result.scheme in ('http', 'https') and bool(result.netloc):
            return True
        if not result.scheme and bool(re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$', url_string)):
            return True
        return False
    except Exception:
        return False


def normalize_url(url_string):
    """Ensure URL has http/https protocol prefix."""
    if not url_string:
        return None
    url_string = url_string.strip()
    if not url_string.startswith(('http://', 'https://')):
        return f'https://{url_string}'
    return url_string


def parse_date(date_str):
    """Parse date from YYYY-MM-DD format."""
    if not date_str or not str(date_str).strip():
        return None
    try:
        return datetime.strptime(str(date_str).strip(), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


# Context processor for global template variables
@app.context_processor
def inject_global_data():
    today = date.today()
    return {
        'current_year': today.year,
        'today_date': today,
        'valid_statuses': VALID_STATUSES,
        'valid_job_types': VALID_JOB_TYPES,
        'user_name': 'Vignesh'
    }


# Template filters
@app.template_filter('format_date')
def format_date_filter(value, format_str='%d %b %Y'):
    if not value:
        return '—'
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            return value
    return value.strftime(format_str)


@app.template_filter('time_ago')
def time_ago_filter(dt):
    if not dt:
        return ''
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    if diff.days == 0:
        if diff.seconds < 60:
            return 'Just now'
        elif diff.seconds < 3600:
            minutes = diff.seconds // 60
            return f'{minutes}m ago'
        else:
            hours = diff.seconds // 3600
            return f'{hours}h ago'
    elif diff.days == 1:
        return 'Yesterday'
    elif diff.days < 7:
        return f'{diff.days}d ago'
    else:
        return dt.strftime('%d %b %Y')


# ==========================================
# SAFE SCHEMA UPGRADE & MIGRATION
# ==========================================

def ensure_schema():
    """Safely ensures all tables and required columns exist without data loss."""
    # 1. Create all missing tables first (applications, activities)
    db.create_all()

    # 2. Inspect the applications table columns via SQLAlchemy inspector
    try:
        inspector = inspect(db.engine)
        if 'applications' in inspector.get_table_names():
            existing_cols = [col['name'] for col in inspector.get_columns('applications')]
            is_sqlite = db.engine.url.drivername.startswith('sqlite')
            bool_default = '0' if is_sqlite else 'FALSE'

            with db.engine.connect() as conn:
                if 'follow_up_date' not in existing_cols:
                    conn.execute(text("ALTER TABLE applications ADD COLUMN follow_up_date DATE"))
                    conn.commit()
                if 'follow_up_completed' not in existing_cols:
                    conn.execute(text(f"ALTER TABLE applications ADD COLUMN follow_up_completed BOOLEAN DEFAULT {bool_default}"))
                    conn.commit()
    except Exception as e:
        print(f"[Schema Check Info] Column check notice: {e}")

    # 3. Backfill initial activities for existing records if activities table is empty
    try:
        if Activity.query.count() == 0 and Application.query.count() > 0:
            for app_rec in Application.query.all():
                init_act = Activity(
                    application_id=app_rec.id,
                    activity_type='created',
                    description=f"Application submitted for {app_rec.position} ({app_rec.status})",
                    created_at=datetime.combine(app_rec.application_date, datetime.min.time(), tzinfo=timezone.utc)
                )
                db.session.add(init_act)
            db.session.commit()
    except Exception:
        db.session.rollback()


# ==========================================
# HEALTH CHECK
# ==========================================

@app.route('/health')
def health_check():
    """Health check endpoint to verify app and database connectivity."""
    try:
        db.session.execute(text('SELECT 1'))
        return jsonify({'status': 'ok'}), 200
    except Exception:
        return jsonify({'status': 'error', 'message': 'Database connection unavailable'}), 503


# ==========================================
# ROUTES
# ==========================================

@app.route('/')
def dashboard():
    """Dashboard overview page with enhanced metrics and activities."""
    today = date.today()
    week_ago = today - timedelta(days=7)

    # Dynamic Dashboard Statistics
    total_applications = Application.query.count()
    saved_count = Application.query.filter_by(status='Saved').count()
    applied_count = Application.query.filter_by(status='Applied').count()
    screening_count = Application.query.filter_by(status='Screening').count()
    interview_count = Application.query.filter_by(status='Interview').count()
    offer_count = Application.query.filter_by(status='Offer').count()
    rejected_count = Application.query.filter_by(status='Rejected').count()
    withdrawn_count = Application.query.filter_by(status='Withdrawn').count()

    # Rate calculations
    offer_rate = round((offer_count / total_applications * 100), 1) if total_applications > 0 else 0
    # Response rate: Apps that reached screening, interview or offer
    responded_count = screening_count + interview_count + offer_count
    response_rate = round((responded_count / total_applications * 100), 1) if total_applications > 0 else 0

    # Applications submitted in the last 7 days
    apps_this_week = Application.query.filter(Application.application_date >= week_ago).count()

    # Interviews scheduled in the current month
    interviews_this_month = Application.query.filter(
        Application.interview_date.isnot(None),
        db.extract('month', Application.interview_date) == today.month,
        db.extract('year', Application.interview_date) == today.year
    ).count()

    # Status Distribution for Chart.js
    status_counts = {
        'Saved': saved_count,
        'Applied': applied_count,
        'Screening': screening_count,
        'Interview': interview_count,
        'Offer': offer_count,
        'Rejected': rejected_count,
        'Withdrawn': withdrawn_count
    }

    # Follow-ups Due (Today, Overdue, or Tomorrow) and not yet completed
    follow_ups_due = Application.query.filter(
        Application.follow_up_date.isnot(None),
        Application.follow_up_completed == False,
        Application.follow_up_date <= (today + timedelta(days=2))
    ).order_by(Application.follow_up_date.asc()).all()

    # Upcoming Interviews: Future or today dates, sorted nearest first
    upcoming_interviews = Application.query.filter(
        Application.interview_date.isnot(None),
        Application.interview_date >= today
    ).order_by(Application.interview_date.asc()).all()

    # Recent Applications (latest 5)
    recent_applications = Application.query.order_by(
        Application.application_date.desc(),
        Application.created_at.desc()
    ).limit(5).all()

    # Recent Activity Feed (latest 8 across all applications)
    recent_activities = Activity.query.join(Application).order_by(Activity.created_at.desc()).limit(8).all()

    return render_template(
        'dashboard.html',
        total_applications=total_applications,
        saved_count=saved_count,
        applied_count=applied_count,
        screening_count=screening_count,
        interview_count=interview_count,
        offer_count=offer_count,
        rejected_count=rejected_count,
        withdrawn_count=withdrawn_count,
        offer_rate=offer_rate,
        response_rate=response_rate,
        apps_this_week=apps_this_week,
        interviews_this_month=interviews_this_month,
        status_counts=status_counts,
        follow_ups_due=follow_ups_due,
        upcoming_interviews=upcoming_interviews,
        recent_applications=recent_applications,
        recent_activities=recent_activities
    )


# ==========================================
# PIPELINE (KANBAN BOARD)
# ==========================================

@app.route('/pipeline')
def pipeline():
    """Kanban-style Application Pipeline page."""
    all_apps = Application.query.order_by(Application.application_date.desc()).all()

    # Group applications by status
    pipeline_groups = {
        'Saved': [],
        'Applied': [],
        'Screening': [],
        'Interview': [],
        'Offer': [],
        'Rejected': [],
        'Withdrawn': []
    }

    for app_item in all_apps:
        status_key = app_item.status if app_item.status in pipeline_groups else 'Applied'
        pipeline_groups[status_key].append(app_item)

    return render_template(
        'pipeline.html',
        pipeline=pipeline_groups,
        total_count=len(all_apps)
    )


@app.route('/applications/<int:id>/update-status', methods=['POST'])
def update_application_status(id):
    """Quick status update route for pipeline and details page."""
    app_record = db.get_or_404(Application, id)
    new_status = request.form.get('status', '').strip()
    return_to = request.form.get('return_to', 'pipeline')

    if new_status in VALID_STATUSES and new_status != app_record.status:
        old_status = app_record.status
        app_record.status = new_status
        app_record.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        # Log Activity
        log_activity(
            app_record.id,
            'status_change',
            f"Status changed from {old_status} to {new_status}"
        )
        flash(f"Updated {app_record.company_name} status to '{new_status}'.", "success")

    if return_to == 'details':
        return redirect(url_for('application_details', id=app_record.id))
    return redirect(url_for('pipeline'))


# ==========================================
# FIND JOBS
# ==========================================

@app.route('/jobs')
def find_jobs():
    """Curated Job Search & Discovery portal."""
    search_query = request.args.get('q', '').strip().lower()
    location_filter = request.args.get('location', '').strip().lower()
    job_type_filter = request.args.get('job_type', '').strip()

    # Get set of already applied (company_name, position) for visual indicator
    tracked_apps = Application.query.all()
    tracked_lookup = {f"{a.company_name.lower().strip()}_{a.position.lower().strip()}": a.id for a in tracked_apps}

    filtered_jobs = []
    for job in SAMPLE_JOBS_LISTINGS:
        # Search query matching title, company, skills, or description
        if search_query:
            skills_str = ' '.join(job['skills']).lower()
            combined_text = f"{job['company_name']} {job['position']} {job['description']} {skills_str}".lower()
            if search_query not in combined_text:
                continue

        # Location filter
        if location_filter and location_filter not in job['location'].lower():
            continue

        # Job type filter
        if job_type_filter and job_type_filter.lower() != job['job_type'].lower():
            continue

        # Check if already tracked
        lookup_key = f"{job['company_name'].lower().strip()}_{job['position'].lower().strip()}"
        job_copy = job.copy()
        job_copy['is_applied'] = lookup_key in tracked_lookup
        job_copy['existing_app_id'] = tracked_lookup.get(lookup_key)
        filtered_jobs.append(job_copy)

    return render_template(
        'jobs.html',
        jobs=filtered_jobs,
        total_jobs=len(filtered_jobs),
        search_query=request.args.get('q', ''),
        selected_location=request.args.get('location', ''),
        selected_job_type=job_type_filter
    )


@app.route('/jobs/apply-confirm', methods=['POST'])
def job_apply_confirm():
    """Creates a new application directly from Find Jobs 'I've Applied' action."""
    company_name = request.form.get('company_name', '').strip()
    position = request.form.get('position', '').strip()
    location = request.form.get('location', '').strip()
    job_type = request.form.get('job_type', 'Full-time').strip()
    job_url = request.form.get('job_url', '').strip()
    app_date_str = request.form.get('application_date', '').strip()
    follow_up_date_str = request.form.get('follow_up_date', '').strip()
    notes = request.form.get('notes', '').strip()

    if not company_name or not position:
        flash("Company name and position are required to track an application.", "error")
        return redirect(url_for('find_jobs'))

    # Check for duplicate tracking
    existing = Application.query.filter(
        Application.company_name.ilike(company_name),
        Application.position.ilike(position)
    ).first()

    if existing:
        flash(f"You already have an active application for {company_name} ({position}).", "info")
        return redirect(url_for('application_details', id=existing.id))

    app_date = parse_date(app_date_str) or date.today()
    follow_up_date = parse_date(follow_up_date_str)

    try:
        new_app = Application(
            company_name=company_name,
            position=position,
            location=location if location else None,
            job_type=job_type,
            application_date=app_date,
            job_url=normalize_url(job_url),
            status='Applied',
            follow_up_date=follow_up_date,
            notes=notes if notes else f"Discovered and applied via JobTrack Find Jobs portal."
        )
        db.session.add(new_app)
        db.session.commit()

        # Log Activity
        log_activity(
            new_app.id,
            'created',
            f"Application submitted via official company careers portal"
        )

        flash(f"Application for {company_name} added to your tracker.", "success")
        return redirect(url_for('application_details', id=new_app.id))
    except Exception as e:
        db.session.rollback()
        flash("Failed to save application. Please try again.", "error")
        return redirect(url_for('find_jobs'))


# ==========================================
# APPLICATIONS (LIST, ADD, DETAILS, EDIT, DELETE)
# ==========================================

@app.route('/applications')
def applications():
    """List all job applications with search, filter, and sort."""
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    job_type_filter = request.args.get('job_type', '').strip()
    sort_order = request.args.get('sort', 'newest').strip()

    query = Application.query

    # Search filter (case-insensitive across company, position, location)
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Application.company_name.ilike(search_pattern),
                Application.position.ilike(search_pattern),
                Application.location.ilike(search_pattern)
            )
        )

    # Status filter
    if status_filter and status_filter in VALID_STATUSES:
        query = query.filter(Application.status == status_filter)

    # Job Type filter
    if job_type_filter and job_type_filter in VALID_JOB_TYPES:
        query = query.filter(Application.job_type == job_type_filter)

    # Sorting
    if sort_order == 'oldest':
        query = query.order_by(Application.application_date.asc(), Application.created_at.asc())
    else:
        query = query.order_by(Application.application_date.desc(), Application.created_at.desc())

    applications_list = query.all()
    total_count = len(applications_list)

    return render_template(
        'applications.html',
        applications=applications_list,
        total_count=total_count,
        search_query=search_query,
        selected_status=status_filter,
        selected_job_type=job_type_filter,
        selected_sort=sort_order
    )


@app.route('/applications/add', methods=['GET', 'POST'])
def add_application():
    """Add a new job application."""
    if request.method == 'POST':
        company_name = request.form.get('company_name', '').strip()
        position = request.form.get('position', '').strip()
        location = request.form.get('location', '').strip()
        job_type = request.form.get('job_type', 'Full-time').strip()
        app_date_str = request.form.get('application_date', '').strip()
        job_url = request.form.get('job_url', '').strip()
        status = request.form.get('status', 'Applied').strip()
        interview_date_str = request.form.get('interview_date', '').strip()
        follow_up_date_str = request.form.get('follow_up_date', '').strip()
        notes = request.form.get('notes', '').strip()

        # Validation
        errors = []
        if not company_name:
            errors.append("Company name is required.")
        if not position:
            errors.append("Position is required.")

        app_date = parse_date(app_date_str)
        if not app_date:
            errors.append("A valid application date is required (YYYY-MM-DD).")

        if status not in VALID_STATUSES:
            status = 'Applied'

        if job_type not in VALID_JOB_TYPES:
            job_type = 'Full-time'

        if job_url and not validate_url(job_url):
            errors.append("Please enter a valid Job URL.")
        else:
            job_url = normalize_url(job_url)

        interview_date = None
        if interview_date_str:
            interview_date = parse_date(interview_date_str)
            if not interview_date:
                errors.append("Interview date must be a valid date (YYYY-MM-DD).")

        follow_up_date = None
        if follow_up_date_str:
            follow_up_date = parse_date(follow_up_date_str)
            if not follow_up_date:
                errors.append("Follow-up date must be a valid date (YYYY-MM-DD).")

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template(
                'add_application.html',
                form_data=request.form,
                today_str=date.today().strftime('%Y-%m-%d')
            ), 400

        try:
            new_app = Application(
                company_name=company_name,
                position=position,
                location=location if location else None,
                job_type=job_type,
                application_date=app_date,
                job_url=job_url if job_url else None,
                status=status,
                interview_date=interview_date,
                follow_up_date=follow_up_date,
                notes=notes if notes else None
            )
            db.session.add(new_app)
            db.session.commit()

            # Log Initial Activity
            log_activity(
                new_app.id,
                'created',
                f"Application tracked with status '{status}'"
            )
            if interview_date:
                log_activity(
                    new_app.id,
                    'interview_scheduled',
                    f"Interview scheduled for {interview_date.strftime('%d %b %Y')}"
                )

            flash("Application added successfully.", "success")
            return redirect(url_for('applications'))
        except Exception as e:
            db.session.rollback()
            flash("Something went wrong while saving the application. Please try again.", "error")
            return render_template('add_application.html', form_data=request.form, today_str=date.today().strftime('%Y-%m-%d')), 500

    today_str = date.today().strftime('%Y-%m-%d')
    suggested_followup = (date.today() + timedelta(days=7)).strftime('%Y-%m-%d')
    return render_template('add_application.html', form_data={}, today_str=today_str, suggested_followup=suggested_followup)


@app.route('/applications/<int:id>')
def application_details(id):
    """View details of a single job application with activity timeline."""
    app_record = db.get_or_404(Application, id)
    activities = Activity.query.filter_by(application_id=id).order_by(Activity.created_at.desc()).all()
    return render_template('application_details.html', application=app_record, activities=activities)


@app.route('/applications/edit/<int:id>', methods=['GET', 'POST'])
def edit_application(id):
    """Edit an existing job application."""
    app_record = db.get_or_404(Application, id)

    if request.method == 'POST':
        company_name = request.form.get('company_name', '').strip()
        position = request.form.get('position', '').strip()
        location = request.form.get('location', '').strip()
        job_type = request.form.get('job_type', 'Full-time').strip()
        app_date_str = request.form.get('application_date', '').strip()
        job_url = request.form.get('job_url', '').strip()
        status = request.form.get('status', 'Applied').strip()
        interview_date_str = request.form.get('interview_date', '').strip()
        follow_up_date_str = request.form.get('follow_up_date', '').strip()
        follow_up_completed = bool(request.form.get('follow_up_completed'))
        notes = request.form.get('notes', '').strip()

        # Validation
        errors = []
        if not company_name:
            errors.append("Company name is required.")
        if not position:
            errors.append("Position is required.")

        app_date = parse_date(app_date_str)
        if not app_date:
            errors.append("A valid application date is required (YYYY-MM-DD).")

        if status not in VALID_STATUSES:
            status = 'Applied'

        if job_type not in VALID_JOB_TYPES:
            job_type = 'Full-time'

        if job_url and not validate_url(job_url):
            errors.append("Please enter a valid Job URL.")
        else:
            job_url = normalize_url(job_url)

        interview_date = None
        if interview_date_str:
            interview_date = parse_date(interview_date_str)
            if not interview_date:
                errors.append("Interview date must be a valid date (YYYY-MM-DD).")

        follow_up_date = None
        if follow_up_date_str:
            follow_up_date = parse_date(follow_up_date_str)
            if not follow_up_date:
                errors.append("Follow-up date must be a valid date (YYYY-MM-DD).")

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('edit_application.html', application=app_record, form_data=request.form), 400

        try:
            # Track meaningful changes for Activity log
            status_changed = (app_record.status != status)
            old_status = app_record.status
            interview_changed = (app_record.interview_date != interview_date) and interview_date is not None
            notes_changed = (app_record.notes != notes) and bool(notes)

            app_record.company_name = company_name
            app_record.position = position
            app_record.location = location if location else None
            app_record.job_type = job_type
            app_record.application_date = app_date
            app_record.job_url = job_url if job_url else None
            app_record.status = status
            app_record.interview_date = interview_date
            app_record.follow_up_date = follow_up_date
            app_record.follow_up_completed = follow_up_completed
            app_record.notes = notes if notes else None
            app_record.updated_at = datetime.now(timezone.utc)

            db.session.commit()

            # Record activities
            if status_changed:
                log_activity(app_record.id, 'status_change', f"Status updated from {old_status} to {status}")
            if interview_changed:
                log_activity(app_record.id, 'interview_scheduled', f"Interview round scheduled for {interview_date.strftime('%d %b %Y')}")
            if notes_changed and not status_changed:
                log_activity(app_record.id, 'note_updated', "Application notes / details updated")

            flash("Application updated successfully.", "success")
            return redirect(url_for('application_details', id=app_record.id))
        except Exception as e:
            db.session.rollback()
            flash("Something went wrong while updating the application.", "error")
            return render_template('edit_application.html', application=app_record, form_data=request.form), 500

    return render_template('edit_application.html', application=app_record, form_data=None)


@app.route('/applications/<int:id>/mark-follow-up-done', methods=['POST'])
def mark_follow_up_done(id):
    """Marks an application's follow-up as completed."""
    app_record = db.get_or_404(Application, id)
    app_record.follow_up_completed = True
    app_record.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    log_activity(
        app_record.id,
        'follow_up_done',
        f"Follow-up with {app_record.company_name} recruiter completed"
    )
    flash(f"Follow-up for {app_record.company_name} marked as completed!", "success")

    return_to = request.form.get('return_to', 'dashboard')
    if return_to == 'details':
        return redirect(url_for('application_details', id=app_record.id))
    return redirect(url_for('dashboard'))


@app.route('/applications/delete/<int:id>', methods=['POST'])
def delete_application(id):
    """Delete a job application."""
    app_record = db.get_or_404(Application, id)
    try:
        company_name = app_record.company_name
        db.session.delete(app_record)
        db.session.commit()
        flash(f"Application for {company_name} deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Something went wrong. Application could not be deleted.", "error")
    return redirect(url_for('applications'))


# ==========================================
# SETTINGS & SAMPLE DATA
# ==========================================

@app.route('/settings')
def settings():
    """Application Settings, Preferences, and Data Management page."""
    total_count = Application.query.count()
    return render_template('settings.html', total_count=total_count)


def seed_sample_data_records():
    """Populates realistic initial sample applications with screening and follow-ups."""
    today = date.today()

    sample_items = [
        {
            'company_name': 'TCS',
            'position': 'Software Developer',
            'location': 'Chennai',
            'job_type': 'Full-time',
            'application_date': today - timedelta(days=12),
            'job_url': 'https://www.tcs.com/careers',
            'status': 'Interview',
            'interview_date': today + timedelta(days=2),
            'follow_up_date': today + timedelta(days=3),
            'follow_up_completed': False,
            'notes': 'Technical Round 1 scheduled. Topics: Python, Data Structures, OOP concepts.'
        },
        {
            'company_name': 'Infosys',
            'position': 'Python Developer',
            'location': 'Bangalore',
            'job_type': 'Full-time',
            'application_date': today - timedelta(days=10),
            'job_url': 'https://www.infosys.com/careers',
            'status': 'Interview',
            'interview_date': today + timedelta(days=4),
            'follow_up_date': today + timedelta(days=5),
            'follow_up_completed': False,
            'notes': 'Online assessment passed. Live coding round with Senior Engineering Lead.'
        },
        {
            'company_name': 'Zoho',
            'position': 'Software Engineer',
            'location': 'Chennai',
            'job_type': 'Full-time',
            'application_date': today - timedelta(days=25),
            'job_url': 'https://www.zoho.com/careers',
            'status': 'Offer',
            'interview_date': today - timedelta(days=5),
            'follow_up_date': None,
            'follow_up_completed': True,
            'notes': 'Received formal offer letter! CTC discussions completed. Pending joining date confirmation.'
        },
        {
            'company_name': 'Freshworks',
            'position': 'Backend Engineer',
            'location': 'Chennai',
            'job_type': 'Full-time',
            'application_date': today - timedelta(days=4),
            'job_url': 'https://www.freshworks.com/careers',
            'status': 'Screening',
            'interview_date': None,
            'follow_up_date': today,
            'follow_up_completed': False,
            'notes': 'Recruiter phone screening scheduled for this afternoon.'
        },
        {
            'company_name': 'Google Cloud',
            'position': 'Cloud Solutions Architect',
            'location': 'Hyderabad',
            'job_type': 'Full-time',
            'application_date': today - timedelta(days=1),
            'job_url': 'https://careers.google.com',
            'status': 'Applied',
            'interview_date': None,
            'follow_up_date': today + timedelta(days=7),
            'follow_up_completed': False,
            'notes': 'Submitted via referral from university alumni.'
        },
        {
            'company_name': 'Atlassian',
            'position': 'Frontend Engineer (Jira)',
            'location': 'Bangalore',
            'job_type': 'Full-time',
            'application_date': today - timedelta(days=3),
            'job_url': 'https://www.atlassian.com/company/careers',
            'status': 'Saved',
            'interview_date': None,
            'follow_up_date': None,
            'follow_up_completed': False,
            'notes': 'Opportunity saved to review portfolio projects before submitting.'
        },
        {
            'company_name': 'Wipro',
            'position': 'Data Analyst',
            'location': 'Hyderabad',
            'job_type': 'Full-time',
            'application_date': today - timedelta(days=18),
            'job_url': 'https://careers.wipro.com',
            'status': 'Rejected',
            'interview_date': None,
            'follow_up_date': None,
            'follow_up_completed': True,
            'notes': 'Application reviewed. Position placed on hold for candidate with 3+ years experience.'
        },
        {
            'company_name': 'Accenture',
            'position': 'Associate Software Engineer',
            'location': 'Bangalore',
            'job_type': 'Full-time',
            'application_date': today - timedelta(days=20),
            'job_url': 'https://www.accenture.com/careers',
            'status': 'Withdrawn',
            'interview_date': None,
            'follow_up_date': None,
            'follow_up_completed': True,
            'notes': 'Withdrew after accepting another opportunity with closer location.'
        }
    ]

    count = 0
    for item in sample_items:
        exists = Application.query.filter_by(
            company_name=item['company_name'],
            position=item['position']
        ).first()
        if not exists:
            app_obj = Application(**item)
            db.session.add(app_obj)
            db.session.flush()

            # Add sample activity
            act = Activity(
                application_id=app_obj.id,
                activity_type='created',
                description=f"Application submitted for {app_obj.position} ({app_obj.status})",
                created_at=datetime.combine(app_obj.application_date, datetime.min.time(), tzinfo=timezone.utc)
            )
            db.session.add(act)
            count += 1
    db.session.commit()
    return count


@app.route('/seed-data', methods=['POST'])
def seed_data_route():
    """Seed sample data through UI button."""
    count = seed_sample_data_records()
    if count > 0:
        flash(f"Successfully populated {count} sample job applications!", "success")
    else:
        flash("Sample data already exists in database.", "info")
    return redirect(url_for('dashboard'))


@app.route('/clear-data', methods=['POST'])
def clear_data_route():
    """Clear all applications from the database."""
    try:
        num_act = db.session.query(Activity).delete()
        num_apps = db.session.query(Application).delete()
        db.session.commit()
        flash(f"Cleared {num_apps} applications from database.", "success")
    except Exception:
        db.session.rollback()
        flash("Failed to clear data.", "error")
    return redirect(url_for('dashboard'))


@app.cli.command('seed-db')
def seed_db_command():
    """CLI command to seed sample applications: flask seed-db"""
    count = seed_sample_data_records()
    print(f"Successfully populated {count} sample applications.")


# ==========================================
# ERROR HANDLERS
# ==========================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


# ==========================================
# INITIALIZATION
# ==========================================

with app.app_context():
    ensure_schema()
    if Application.query.count() == 0:
        seed_sample_data_records()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '127.0.0.1')
    debug = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    print(f"[JobTrack] Application running at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
