# JobTrack – Job Application Tracker

> **"Track every application. Stay organized. Get hired."**

A modern, clean, and responsive web-based Job Search & Application Management platform designed for students and job seekers to discover tech opportunities, track hiring pipeline stages, manage recruiter follow-ups, and monitor interview schedules.

---

## 🚀 Key Features

- **📊 Comprehensive Dashboard Analytics**:
  - Live statistics: *Total Applications*, *Active Applications*, *Interviews*, *Offers*, *Applications This Week*, *Interviews This Month*, and *Response Rate (%)*.
  - Interactive status breakdown doughnut chart powered by Chart.js.
  - **Follow-ups Due**: Immediate alerts for recruiter follow-ups with 1-click completion.
  - **Upcoming Interviews**: Automated schedule countdown badges for upcoming rounds.
  - **Live Activity Feed**: Real-time chronological audit trail of status updates and events.

- **📌 Kanban Application Pipeline (`/pipeline`)**:
  - Visual 5-column Kanban board (*Saved*, *Applied*, *Screening*, *Interview*, *Offer*).
  - Concluded / archived section for *Rejected* and *Withdrawn* opportunities.
  - Quick-move stage dropdown on each card and direct click-through to details.

- **🔍 "Find Jobs" Discovery Portal (`/jobs`)**:
  - Discover curated tech job opportunities across locations and job types.
  - Direct **"Apply ↗"** buttons that open official company careers portals in a new tab.
  - **"I've Applied" One-Click Logging**: Confirmation modal pre-fills details, sets follow-up reminders, prevents duplicates, and logs the application directly to your SQLite database.

- **📝 Complete Application Management (CRUD)**:
  - **Add Application**: Track company name, position, location, job type, application date, status, job URL, interview dates, follow-up dates, and notes.
  - **Application Details**: 4-stage visual progress timeline (*Applied* &rarr; *Screening* &rarr; *Interview* &rarr; *Offer*), external job link, and full **Activity History Timeline**.
  - **Edit & Delete**: Modify dates, notes, and stages with pre-filled forms; safe deletion with confirmation modals.

- **🔔 Follow-up Reminder System**:
  - Set custom follow-up dates to stay proactive with recruiters.
  - Visual badges for *Overdue*, *Today*, and *Upcoming* follow-ups with 1-click completion.

- **🌗 Dark Mode & Light Mode**:
  - Full theme switcher with seamless persistence in `localStorage`.
  - Professional high-contrast slate dark theme (`#0F172A`).

- **📱 Fully Responsive SaaS UI**:
  - Desktop sidebar, mobile slide-out navigation with backdrop.
  - Fluid grid layouts, accessible controls, and smooth toast notifications.

---

## 🛠️ Tech Stack

- **Backend**: Python 3, Flask
- **Database**: SQLite 3, Flask-SQLAlchemy (ORM) with automated schema migrations
- **Frontend**: HTML5, CSS3, Vanilla JavaScript, Jinja2 Templates
- **Charts & Visuals**: Chart.js (CDN), Font Awesome 6 (CDN), Google Fonts (Inter)
- **Environment**: `python-dotenv`

---

## 📁 Project Structure

```text
Job-Application-Tracker/
│
├── app.py                     # Flask application, SQLAlchemy models (Application, Activity), routes
├── requirements.txt           # Python package dependencies
├── README.md                  # Project documentation
├── .gitignore                 # Git ignore configuration
├── .env.example               # Environment variable template
├── test_app.py                # Automated unit & integration test suite (12 test cases)
├── verify_app.py              # End-to-end verification script
│
├── templates/                 # Jinja2 HTML templates
│   ├── base.html              # Core SaaS shell: sidebar, top header, toasts, modal, dark mode
│   ├── dashboard.html         # Dashboard stats, follow-ups, activity feed, Chart.js overview
│   ├── jobs.html              # Find Jobs portal with official links & "I've Applied" modal
│   ├── pipeline.html          # Kanban pipeline board with 5 active stages & archive
│   ├── applications.html      # Application list table with search, filter, and sort
│   ├── add_application.html   # Add new job application form
│   ├── edit_application.html  # Edit existing application form
│   ├── application_details.html # Single application view with timeline & activity log
│   ├── settings.html          # Theme switcher (Dark/Light) and database management
│   ├── 404.html               # 404 Page Not Found
│   ├── 500.html               # 500 Internal Server Error
│   └── partials/
│       └── pipeline_card.html # Reusable Kanban card component
│
├── static/
│   ├── css/
│   │   └── style.css          # SaaS dashboard styles, color variables, dark mode, responsive layout
│   │
│   └── js/
│       └── script.js          # Theme switcher, Chart.js, mobile sidebar, modals, toasts
│
├── database/
│   ├── .gitkeep
│   └── jobtrack.db            # Local SQLite database
│
└── screenshots/
    └── .gitkeep
```

---

## 💻 Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/vignesh582/Job-Application-Tracker.git
cd Job-Application-Tracker
```

### 2. Create and activate a Python virtual environment
```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Install required dependencies
```powershell
pip install -r requirements.txt
```

### 4. Run the application
```powershell
python app.py
```

### 5. Open in your browser
Navigate to:
```text
http://127.0.0.1:5000
```

---

## 🧪 Seeding Sample Data

To populate the database with realistic sample job applications (TCS, Infosys, Zoho, Freshworks, Google Cloud, Atlassian, Wipro, Accenture):
- **Via Web Interface**: Visit **Settings** &rarr; click **"Populate Verified Sample Records"**
- **Via CLI**:
  ```powershell
  flask seed-db
  ```

---

## 🔒 License & Credits

Developed with ❤️ by **Vignesh** for the JobTrack Application Tracker platform.
