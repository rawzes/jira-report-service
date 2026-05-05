# 🚀 Jira Report Service

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI/CD](https://github.com/rawzes/jira-report-service/actions/workflows/ci.yml/badge.svg)](https://github.com/rawzes/jira-report-service/actions)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Production-ready service for generating Jira reports focused on flow-analytics rather than velocity and estimate-based planning.**

Built with **FastAPI**, **httpx**, **pydantic**, and **Jinja2** for HTML report generation.

---

## 📊 Flow-Analytics Focus

This report is designed for teams that don't use story points or estimates. Instead, it focuses on **flow metrics** to understand and improve the software delivery process:

| Metric | Description |
|--------|-------------|
| **Throughput** | Number of tasks completed per week |
| **Cycle Time** | Time from starting work to completion |
| **WIP** | Number of active tasks |
| **Aging WIP** | How long tasks have been open |
| **Overdue Tasks** | Tasks past their due date |
| **Reopened Tasks** | Tasks that were completed but reopened |

These metrics help identify bottlenecks, predict delivery dates, and improve process efficiency without relying on estimates.

---

## ✨ Features

### Core Metrics
- **Worklog Hours** - Track time spent per employee and project
- **Created/Closed Tasks** - Monitor task flow per month
- **Throughput** - Weekly completed tasks count
- **Cycle Time** - Median and 85th percentile with detailed tracking
- **WIP Analysis** - Current work-in-progress snapshot with aging analysis

### Flow Metrics
- **Weekly Throughput** - Tasks closed per week with net flow calculation
- **Cycle Time Analysis** - Time from "In Progress" to "Done" with median/P85
- **Aging WIP** - All non-closed tasks with age in days
- **Overdue Tasks** - Tasks past due date with days overdue
- **Reopened Rate** - Tasks reopened after completion with counts
- **Blocked Tasks** - Tasks in blocked/on-hold/waiting statuses

### Report Slices
- **By Employee** - Individual performance metrics
- **By Project** - MB / MAX / IB project breakdown
- **By Week** - Weekly throughput analysis
- **By Issue Type** - Bug / Task / Story / Support / Tech (if available)

### HTML Report Sections
1. **Summary** - Key metrics overview with top-5 oldest issues
2. **By Employee** - Per-employee metrics with WIP and cycle time
3. **By Project** - Per-project flow metrics with aging buckets
4. **Weekly Throughput** - Week-by-week closed vs created tasks
5. **Cycle Time** - Detailed cycle time per issue
6. **Aging WIP** - All open tasks with age analysis
7. **Overdue** - Past-due tasks with priority
8. **Reopened** - Reopened tasks with dates and counts

### Technical Features
- **Multi-Format Output** - Returns HTML or JSON based on `format` parameter
- **Changelog Analysis** - Full history parsing for cycle time and reopened calculations
- **Configurable Statuses** - Define start, done, and blocked statuses via environment
- **Multi-Language** - Support for English and Russian report output
- **Resilient API Client** - Retry logic with exponential backoff, rate limiting
- **Pagination Support** - Handles Jira API pagination for search, worklogs, and changelogs
- **Timezone Aware** - All calculations in Europe/Minsk timezone

---

## 🏗️ Architecture

```
jira-report-service/
├── app/
│   ├── main.py                    # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── report.py             # Report generation endpoints (HTML + JSON)
│   ├── services/
│   │   ├── jira_client.py        # Jira API client with retry logic and changelog support
│   │   ├── report_builder.py     # Flow metrics aggregation and calculations
│   │   └── html_exporter.py     # HTML file generation with Jinja2 templates
│   ├── templates/
│   │   └── index.html           # Jinja2 HTML template for reports
│   └── models/
│       ├── __init__.py
│       ├── config.py             # Pydantic settings from environment
│       └── schemas.py            # Pydantic models for all data structures
├── tests/
│   ├── __init__.py
│   └── test_report_builder.py    # Unit tests
├── scripts/
│   ├── setup-venv.sh            # Linux/macOS setup script
│   └── setup-venv.ps1           # Windows PowerShell setup script
├── .github/
│   └── workflows/
│       └── ci.yml                # CI/CD pipeline
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Jira Cloud account with API token
- Docker (optional, for containerized deployment)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rawzes/jira-report-service.git
   cd jira-report-service
   ```

2. **Set up environment:**
   ```bash
   # Copy example env file
   cp .env.example .env
   
   # Edit with your credentials
   nano .env
   ```

3. **Configure your Jira credentials in `.env`:**
   ```env
   JIRA_BASE_URL=https://your-domain.atlassian.net
   JIRA_EMAIL=your-email@example.com
   JIRA_API_TOKEN=your-api-token
   JIRA_PROJECT_KEYS=MB,MAX,IB
   JIRA_DONE_STATUSES=Done,Closed,Resolved
   JIRA_START_STATUSES=In Progress,In Review,In Testing
   JIRA_BLOCKED_STATUSES=Blocked,On Hold,Waiting
   TIMEZONE=Europe/Minsk
   REPORT_LANG=ru
   ```

### Running Locally

#### Option 1: Using Virtual Environment (Recommended for Development)

**macOS/Linux:**
```bash
bash scripts/setup-venv.sh
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Windows (PowerShell):**
```powershell
.\scripts\setup-venv.ps1
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Option 2: Using Docker
```bash
docker-compose up -d
```

#### Access the Service
Open http://localhost:8000 in your browser.

---

## 📚 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### API Endpoints

#### POST /reports/monthly
Generate monthly report.

**Request Body:**
```json
{
  "year": 2024,
  "month": 1,
  "project_keys": ["MB", "MAX", "IB"],
  "group_by_projects": true,
  "include_raw_data": true
}
```

**Query Parameters:**
- `lang`: Language for report (en, ru) - default: ru
- `format`: Response format (html, htmldownload, json) - default: html

#### GET /reports/monthly
Generate monthly report via GET.

**Query Parameters:**
- `year`: Report year (required)
- `month`: Report month 1-12 (required)
- `project_keys`: Comma-separated project keys (optional)
- `group_by_projects`: Group by projects (default: true)
- `include_raw_data`: Include raw data sheets (default: true)
- `lang`: Language for report (en, ru) - default: ru
- `format`: Response format (html, htmldownload, json) - default: html

#### POST /reports/custom
Generate custom date range report.

**Request Body:**
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "project_keys": ["MB", "MAX", "IB"],
  "group_by_projects": true,
  "include_raw_data": true
}
```

#### GET /reports/health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "jira-report"
}
```

---

## 🧪 Testing

```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

---

## 📖 Example Usage

### Using curl (HTML format)
```bash
curl -X POST "http://localhost:8000/reports/monthly?lang=ru&format=html" \
  -H "Content-Type: application/json" \
  -d '{
    "year": 2024,
    "month": 1,
    "project_keys": ["MB", "MAX", "IB"]
  }'
```

### Using curl (HTML download)
```bash
curl -X POST "http://localhost:8000/reports/monthly?lang=ru&format=htmldownload" \
  -H "Content-Type: application/json" \
  -d '{
    "year": 2024,
    "month": 1,
    "project_keys": ["MB", "MAX", "IB"]
  }' \
  -o "jira_report_2024_01.html"
```

### Using Python
```python
import requests

# HTML format (view in browser)
response = requests.post(
    "http://localhost:8000/reports/monthly?format=html",
    json={
        "year": 2024,
        "month": 1,
        "project_keys": ["MB", "MAX", "IB"]
    }
)

# HTML download
response = requests.post(
    "http://localhost:8000/reports/monthly?format=htmldownload",
    json={
        "year": 2024,
        "month": 1,
        "project_keys": ["MB", "MAX", "IB"]
    }
)

with open("jira_report_2024_01.html", "wb") as f:
    f.write(response.content)

# JSON format
response = requests.post(
    "http://localhost:8000/reports/monthly?format=json",
    json={
        "year": 2024,
        "month": 1,
        "project_keys": ["MB", "MAX", "IB"]
    }
)

report_data = response.json()
print(f"Total worklog hours: {report_data['total_worklog_hours']}")
print(f"Median cycle time: {report_data['median_cycle_time']}")
```

---

## 🔧 Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `JIRA_BASE_URL` | Your Jira Cloud instance URL | Required |
| `JIRA_EMAIL` | Your Jira account email | Required |
| `JIRA_API_TOKEN` | Your Jira API token | Required |
| `JIRA_PROJECT_KEYS` | Comma-separated project keys | MB,MAX,IB |
| `JIRA_DONE_STATUSES` | Comma-separated done statuses | Done,Closed,Resolved |
| `JIRA_START_STATUSES` | Comma-separated start progress statuses | In Progress,In Review,In Testing |
| `JIRA_BLOCKED_STATUSES` | Comma-separated blocked statuses | Blocked,On Hold,Waiting |
| `TIMEZONE` | Timezone for date calculations | Europe/Minsk |
| `REPORT_LANG` | Report language (en, ru) | ru |

### Getting Jira API Token
1. Log in to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Name your token and copy it immediately

---

## 📊 Calculation Rules

- **No Estimates**: If no story points/estimates exist, velocity and estimate-based metrics are not calculated
- **Throughput**: Counts only actually closed tasks
- **Cycle Time**: Calculated only for tasks that reached final status
- **Aging WIP**: Counts only non-closed tasks
- **Reopened Task**: Task that had a final status then moved back to non-final status
- **Blocked Task**: Task currently in configured blocked statuses
- **Configurable Statuses**: Start, done, and blocked statuses are configurable via environment variables
- **Changelog Required**: Cycle time and reopened rate use changelog/history
- **Full Changelog**: Changelog is fully fetched with pagination support
- **Timezone**: All date ranges work correctly with Europe/Minsk timezone

---

## ⚙️ Jira API Considerations

### Changelog API
- Full changelog is fetched for each issue to calculate cycle time and reopened rate
- Handles paginated changelog responses
- Parses all status transitions to find start progress and done dates

### Pagination
- Search API (`/rest/api/3/search/jql`): Uses `nextPageToken` for pagination
- Worklog API (`/rest/api/3/issue/{key}/worklog`): Handles pagination up to 1000 per page
- Changelog: Fetches complete history with pagination support

### Rate Limiting
- Jira Cloud API has rate limits (typically 1000 requests per hour per API token)
- The service implements:
  - Exponential backoff retry (5 attempts, 4-60 second delays)
  - Semaphore-based concurrency limiting (max 10 concurrent requests)
  - Automatic retry on 429 (Rate Limited) responses
  - Request timeouts (30s timeout, 10s connect timeout)

---

## 🛠️ Development

### Key Design Decisions

1. **Flow-Analytics First** - Report focuses on flow metrics, not velocity
2. **Async Architecture** - Uses `httpx.AsyncClient` for non-blocking HTTP requests
3. **Changelog Parsing** - Full history analysis for accurate cycle time
4. **Context Manager** - JiraClient uses async context manager for proper cleanup
5. **Semaphore Limiting** - Limits concurrent API requests to avoid rate limits
6. **Timezone Handling** - Uses `zoneinfo` for proper timezone conversion
7. **Configurable Statuses** - All status lists configurable via environment
8. **Multi-Language** - Support for English and Russian via `REPORT_LANG`
9. **Dual Output** - Returns HTML or JSON based on `format` parameter
10. **HTML Templates** - Uses Jinja2 for flexible HTML report generation

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📞 Contact & Support

**Author**: Senior Backend Engineer

**Email**: [rawzes@gmail.com](mailto:rawzes@gmail.com)

**Project Repository**: [https://github.com/rawzes/jira-report-service](https://github.com/rawzes/jira-report-service)

**Issues & Bug Reports**: [GitHub Issues](https://github.com/rawzes/jira-report-service/issues)

**Feature Requests**: [GitHub Discussions](https://github.com/rawzes/jira-report-service/discussions)

---

## 🎯 Badges & Buttons

[![GitHub stars](https://img.shields.io/github/stars/rawzes/jira-report-service.svg?style=social&label=Star)](https://github.com/rawzes/jira-report-service)
[![GitHub forks](https://img.shields.io/github/forks/rawzes/jira-report-service.svg?style=social&label=Fork)](https://github.com/rawzes/jira-report-service/fork)
[![GitHub watchers](https://img.shields.io/github/watchers/rawzes/jira-report-service.svg?style=social&label=Watch)](https://github.com/rawzes/jira-report-service)

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/rawzes)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-30363D?style=for-the-badge&logo=GitHub-Sponsors&logoColor=#EA4AAA)](https://github.com/sponsors/rawzes)

---

**Note**: This service is designed for Jira Cloud REST API (API v3). For Jira Server/Data Center, you may need to adjust the API endpoints and authentication method.

**Important**: This report is oriented on **flow-analytics** of the process (throughput, cycle time, WIP, aging WIP, overdue, reopened) rather than velocity and estimate-based planning.
