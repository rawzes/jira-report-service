# Jira Report Service

Production-ready service for generating Jira reports focused on **flow-analytics** rather than velocity and estimate-based planning. Built with FastAPI, httpx, pydantic, and openpyxl.

## Flow-Analytics Focus

This report is designed for teams that don't use story points or estimates. Instead, it focuses on **flow metrics** to understand and improve the software delivery process:

- **Throughput**: Number of tasks completed per week
- **Cycle Time**: Time from starting work to completion
- **WIP (Work in Progress)**: Number of active tasks
- **Aging WIP**: How long tasks have been open
- **Overdue Tasks**: Tasks past their due date
- **Reopened Tasks**: Tasks that were completed but reopened

These metrics help identify bottlenecks, predict delivery dates, and improve process efficiency without relying on estimates.

## Features

### Core Metrics
- **Worklog Hours**: Track time spent per employee and project
- **Created/Closed Tasks**: Monitor task flow per month
- **Throughput**: Weekly completed tasks count
- **Cycle Time**: Median and 85th percentile with detailed tracking
- **WIP Analysis**: Current work-in-progress snapshot with aging analysis

### Flow Metrics
- **Weekly Throughput**: Tasks closed per week with net flow calculation
- **Cycle Time Analysis**: Time from "In Progress" to "Done" with median/P85
- **Aging WIP**: All non-closed tasks with age in days
- **Overdue Tasks**: Tasks past due date with days overdue
- **Reopened Rate**: Tasks reopened after completion with counts
- **Blocked Tasks**: Tasks in blocked/on-hold/waiting statuses

### Report Slices
- By Employee: Individual performance metrics
- By Project: MB / MAX / IB project breakdown
- By Week: Weekly throughput analysis
- By Issue Type: Bug / Task / Story / Support / Tech (if available)

### XLSX Report Sheets
1. **Summary**: Key metrics overview with top-5 oldest issues
2. **By Employee**: Per-employee metrics with WIP and cycle time
3. **By Project**: Per-project flow metrics with aging buckets
4. **Weekly Throughput**: Week-by-week closed vs created tasks
5. **Cycle Time**: Detailed cycle time per issue
6. **Aging WIP**: All open tasks with age analysis
7. **Overdue**: Past-due tasks with priority
8. **Reopened**: Reopened tasks with dates and counts
9. **Raw Issues**: Complete issue data export
10. **Raw Worklogs**: Complete worklog data export
11. **Raw Transitions**: All status transitions history
12. **Risks**: Automated risk flags and warnings
13. **Charts**: Visual charts for key metrics

### Visual Charts (in XLSX)
- Column chart: Closed tasks by week and project
- Line chart: Median cycle time by week
- Bar chart: Worklog hours by employee
- Bar chart: Aging WIP buckets (0-7, 8-14, 15-30, 30+ days)
- Stacked bar: Status distribution by project
- Bar chart: Reopened tasks by project

### Automated Risk Flags
- Projects with declining throughput (2+ weeks)
- Projects with growing cycle time
- Tasks older than 14 days in active statuses
- Tasks without assignee
- Overdue tasks
- Reopened tasks
- Diagnostic: Employees with high worklog but low closures

### Technical Features
- **Multi-Format Output**: Returns XLSX or JSON based on `format` parameter
- **Changelog Analysis**: Full history parsing for cycle time and reopened calculations
- **Configurable Statuses**: Define start, done, and blocked statuses via environment
- **Multi-Language**: Support for English and Russian report output
- **Resilient API Client**: Retry logic with exponential backoff, rate limiting
- **Pagination Support**: Handles Jira API pagination for search, worklogs, and changelogs
- **Timezone Aware**: All calculations in Europe/Minsk timezone

## Architecture

```
app/
├── main.py                    # FastAPI application entry point
├── api/
│   ├── __init__.py
│   └── report.py             # Report generation endpoints (XLSX + JSON)
├── services/
│   ├── jira_client.py        # Jira API client with retry logic and changelog support
│   ├── report_builder.py     # Flow metrics aggregation and calculations
│   └── xlsx_exporter.py     # Excel file generation with charts
└── models/
    ├── __init__.py
    ├── config.py             # Pydantic settings from environment
    └── schemas.py            # Pydantic models for all data structures
tests/
├── __init__.py
└── test_report_builder.py    # Unit tests
```

## Prerequisites

- Python 3.12+
- Jira Cloud account with API token
- Docker (optional, for containerized deployment)

## Configuration

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` with your Jira credentials and configuration:

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

### Configuration Options

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

## Running Locally

### Using Docker (Recommended)

1. Create `.env` file with your credentials
2. Start the service:

```bash
docker-compose up -d
```

3. Service will be available at http://localhost:8000

### Using Python Directly

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### POST /reports/monthly

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
- `format`: Response format (xlsx, json) - default: xlsx

**Response:** XLSX file download or JSON with report data

### GET /reports/monthly

Generate monthly report via GET.

**Query Parameters:**
- `year`: Report year (required)
- `month`: Report month 1-12 (required)
- `project_keys`: Comma-separated project keys (optional)
- `group_by_projects`: Group by projects (default: true)
- `include_raw_data`: Include raw data sheets (default: true)
- `lang`: Language for report (en, ru) - default: ru
- `format`: Response format (xlsx, json) - default: xlsx

**Response:** XLSX file download or JSON with report data

### POST /reports/custom

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

**Query Parameters:**
- `lang`: Language for report (en, ru) - default: ru
- `format`: Response format (xlsx, json) - default: xlsx

**Response:** XLSX file download or JSON with report data

### GET /reports/health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "jira-report"
}
```

## Example Usage

### Using curl (XLSX format)

```bash
curl -X POST "http://localhost:8000/reports/monthly?lang=ru&format=xlsx" \
  -H "Content-Type: application/json" \
  -d '{
    "year": 2024,
    "month": 1,
    "project_keys": ["MB", "MAX", "IB"]
  }' \
  -o "jira_report_2024_01.xlsx"
```

### Using curl (JSON format)

```bash
curl -X POST "http://localhost:8000/reports/monthly?lang=en&format=json" \
  -H "Content-Type: application/json" \
  -d '{
    "year": 2024,
    "month": 1,
    "project_keys": ["MB", "MAX", "IB"]
  }'
```

### Using Python

```python
import requests

# XLSX format
response = requests.post(
    "http://localhost:8000/reports/monthly?format=xlsx",
    json={
        "year": 2024,
        "month": 1,
        "project_keys": ["MB", "MAX", "IB"]
    }
)

with open("jira_report_2024_01.xlsx", "wb") as f:
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

## XLSX Report Structure

The generated XLSX file contains the following sheets:

### 1. Summary
- Report period information
- Total worklog hours, created issues, closed issues
- Throughput, median cycle time, P85 cycle time
- Overdue, reopened, blocked task counts
- Top 5 oldest open issues

### 2. By Employee
- Employee Name, Account ID, Project Key
- Worklog Hours, Created Tasks, Closed Tasks
- Reopened Tasks, Active WIP
- Avg/Median Cycle Time, Overdue Tasks

### 3. By Project
- Project Key, Worklog Hours, Created/Closed Tasks
- Throughput, Median/P85 Cycle Time
- WIP Count, Aging buckets (7/14/30+ days)
- Reopened, Overdue, Blocked counts

### 4. Weekly Throughput
- Week Start/End, Project Key
- Closed Tasks Count, Created Tasks Count
- Net Flow (Closed - Created)

### 5. Cycle Time
- Issue Key, Project Key, Issue Type
- Assignee, Reporter
- Start Progress Date, Done Date
- Cycle Time (Days/Hours), Reopened Flag

### 6. Aging WIP
- Issue Key, Project Key, Status
- Assignee, Created Date, Last Status Change
- Aging Days, Blocked Flag, Due Date, Overdue Flag

### 7. Overdue
- Issue Key, Project Key, Assignee
- Status, Due Date, Days Overdue, Priority

### 8. Reopened
- Issue Key, Project Key, Assignee
- Done Date, Reopen Date, Reopen Count, Current Status

### 9. Raw Issues (optional)
- Complete issue data with all flow metrics

### 10. Raw Worklogs (optional)
- All worklog entries with details

### 11. Raw Transitions (optional)
- All status transitions with dates and authors

### 12. Risks
- Risk Type, Description, Severity
- Project Key, Employee Name

### 13. Charts
- Visual charts for key metrics

## Calculation Rules

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

## Jira API Considerations

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

## Testing

Run unit tests:

```bash
pytest tests/ -v
```

The test suite covers:
- Flow metrics calculations
- Worklog aggregation per employee
- Created/closed issues counting
- Cycle time calculations
- XLSX generation with all sheets
- Pagination handling
- Edge cases (deleted users, missing assignees)

## Development

### Project Structure Details

- **`app/main.py`**: FastAPI application setup with CORS middleware
- **`app/api/report.py`**: Endpoints for XLSX and JSON report generation
- **`app/services/jira_client.py`**: Async Jira API client with changelog support
- **`app/services/report_builder.py`**: Flow metrics aggregation and calculations
- **`app/services/xlsx_exporter.py`**: Generates formatted Excel with charts
- **`app/models/config.py`**: Pydantic Settings loading from `.env` file
- **`app/models/schemas.py`**: All Pydantic models for requests/responses

### Key Design Decisions

1. **Flow-Analytics First**: Report focuses on flow metrics, not velocity
2. **Async Architecture**: Uses `httpx.AsyncClient` for non-blocking HTTP requests
3. **Changelog Parsing**: Full history analysis for accurate cycle time
4. **Context Manager**: JiraClient uses async context manager for proper cleanup
5. **Semaphore Limiting**: Limits concurrent API requests to avoid rate limits
6. **Timezone Handling**: Uses `zoneinfo` for proper timezone conversion
7. **Configurable Statuses**: All status lists configurable via environment
8. **Multi-Language**: Support for English and Russian via `REPORT_LANG`
9. **Dual Output**: Returns XLSX or JSON based on `format` parameter

## License

MIT

## Author

Senior Backend Engineer

---

**Note**: This service is designed for Jira Cloud REST API (API v3). For Jira Server/Data Center, you may need to adjust the API endpoints and authentication method.

**Important**: This report is oriented on **flow-analytics** of the process (throughput, cycle time, WIP, aging WIP, overdue, reopened) rather than velocity and estimate-based planning.
