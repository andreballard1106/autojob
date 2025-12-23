# 🚀 Automated Job Application System

> Streamline your job search with intelligent automation. Apply to multiple positions in parallel while maintaining personalization and accuracy.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![React](https://img.shields.io/badge/React-18+-61dafb.svg)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔄 **Parallel Processing** | Apply to multiple jobs simultaneously with isolated browser instances |
| 👥 **Team Support** | Multiple user profiles with individual resumes and cover letters |
| 🧠 **Smart Form Filling** | Automatically detects and fills application forms across different sites |
| 🔐 **OTP/CAPTCHA Handling** | Pauses and notifies when human intervention is needed |
| 📊 **Real-time Dashboard** | Monitor all applications with live WebSocket updates |
| 🚫 **Duplicate Prevention** | Never apply to the same job twice |
| 🤖 **AI Cover Letters** | GPT-4 powered personalized cover letter generation |
| 📧 **Email Notifications** | Get notified when applications complete or need attention |

## 🚀 Quick Start (No Docker Required!)

This project uses **SQLite** by default - no database installation needed!

### Prerequisites

- Python 3.11+
- Node.js 18+
- Chrome browser

### Step 1: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Start the server (this also creates the database)
uvicorn app.main:app --reload --port 8000
```

### Step 2: Frontend Setup (new terminal)

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Step 3: Access the Application

- **Dashboard:** http://localhost:5173
- **API Docs:** http://localhost:8000/docs

That's it! No Docker, no PostgreSQL, no Redis needed for development.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (React + TypeScript)               │
│   Dashboard │ Profiles │ Job Queue │ Real-time Notifications    │
└─────────────────────────────────────────────────────────────────┘
                              │ WebSocket + REST API
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI + Python)                  │
│   REST API │ WebSocket │ AI Service │ Notification Service      │
└─────────────────────────────────────────────────────────────────┘
                    │                          │
                    ▼                          ▼
            ┌──────────────┐         ┌─────────────────────┐
            │   SQLite     │         │  Automation Engine  │
            │  (jobapp.db) │         │  (Playwright)       │
            └──────────────┘         └─────────────────────┘
```

## 📁 Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/routes/     # REST API endpoints
│   │   ├── models/         # SQLAlchemy database models
│   │   ├── schemas/        # Pydantic validation schemas
│   │   ├── services/       # Business logic (AI, notifications)
│   │   ├── config.py       # Application configuration
│   │   └── main.py         # FastAPI application
│   ├── automation/
│   │   ├── adapters/       # Site-specific handlers
│   │   ├── orchestrator.py # Main automation controller
│   │   └── browser_manager.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/          # React pages
│   │   ├── stores/         # State management
│   │   └── services/       # API clients
│   └── package.json
└── storage/                # Uploaded files & screenshots
```

## 🔧 Configuration

### Default Settings (in `backend/app/config.py`)

```python
# Database: SQLite (no installation needed)
use_sqlite: bool = True

# Background Processing: Synchronous (no Redis needed)
use_celery: bool = False

# Browser instances
max_concurrent_browsers: int = 5
browser_timeout: int = 300
```

### Enable AI Cover Letters

Update `backend/app/config.py`:

```python
openai_api_key: str = "sk-your-actual-api-key"
enable_ai_cover_letter: bool = True
```

### Production Mode (with PostgreSQL)

For production, set in `backend/app/config.py`:

```python
use_sqlite: bool = False  # Use PostgreSQL
use_celery: bool = True   # Use Redis for background jobs

# PostgreSQL settings
postgres_host: str = "localhost"
postgres_port: int = 5432
postgres_user: str = "jobapp"
postgres_password: str = "qweqwe123"
postgres_db: str = "jobapp"
```

## 🌐 Supported Job Platforms

| Platform | Adapter | Features |
|----------|---------|----------|
| LinkedIn | `linkedin` | Easy Apply, multi-step forms |
| Workday | `workday` | Multi-step, custom questions |
| Greenhouse | `greenhouse` | Single-page, resume upload |
| Lever | `lever` | Single-page, resume parsing |
| Generic | `generic` | Auto-detect, best-effort |

## 📖 How to Use

### 1. Create a Profile
- Go to **Profiles** page
- Click **Add Profile**
- Enter your information and upload resume

### 2. Add Jobs
- Go to **Jobs** page
- Paste job URLs (one per line)
- Select which profile to use
- Click **Add Jobs**

### 3. Start Automation
- Click **Start Processing**
- Watch real-time progress on Dashboard
- When OTP/CAPTCHA appears, solve it and click **Resume**

### 4. Monitor Results
- View success/failure rates on Dashboard
- Check application logs for debugging
- Review confirmation references

## 📖 API Endpoints

### Profiles
- `GET /api/profiles` - List all profiles
- `POST /api/profiles` - Create profile
- `POST /api/profiles/{id}/resume` - Upload resume

### Jobs
- `GET /api/jobs` - List jobs with filters
- `POST /api/jobs/bulk` - Bulk create from URLs
- `POST /api/jobs/start-processing` - Start automation
- `POST /api/jobs/{id}/retry` - Retry failed job

### Dashboard
- `GET /api/dashboard/stats` - Overall statistics
- `GET /api/dashboard/team` - Team overview

### AI Features
- `POST /api/ai/cover-letter` - Generate AI cover letter

### WebSocket
- `ws://localhost:8000/ws` - Real-time updates

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## ⚠️ Disclaimer

This tool is intended for personal use to streamline your job application process. Please:
- Respect rate limits on job sites
- Review applications before final submission when possible
- Follow each site's Terms of Service
- Use responsibly and ethically

## 📝 License

This project is licensed under the MIT License.

---

<p align="center">
  Made with ❤️ for job seekers everywhere
</p>
