# CI and Local Development Setup Plan

## Overview
This plan outlines the steps to:
1. Set up GitHub Actions CI workflow for automated testing and Docker builds
2. Configure local development environment using Python virtual environments

## Task 1: GitHub Actions CI Workflow

### Create `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [ main, master, develop ]
  pull_request:
    branches: [ main, master, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.12]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run tests
      run: |
        pytest tests/ -v
      env:
        JIRA_BASE_URL: https://test.atlassian.net
        JIRA_EMAIL: test@example.com
        JIRA_API_TOKEN: test-token

    - name: Lint with flake8
      run: |
        pip install flake8
        flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 app/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

  docker:
    runs-on: ubuntu-latest
    needs: test
    if: github.event_name == 'push' && (github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master')

    steps:
    - uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Build Docker image
      run: |
        docker build -t jira-report:latest .

    - name: Test Docker image
      run: |
        docker run --rm jira-report:latest python -c "from app.main import app; print('Import successful')"
```

## Task 2: Local Development Setup Script

### Create `scripts/setup-venv.sh` (for macOS/Linux)

```bash
#!/bin/bash

echo "Setting up Python virtual environment for Jira Report Service..."

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Copy .env.example to .env if .env doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from .env.example"
    echo "Please edit .env with your Jira credentials"
fi

echo ""
echo "Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To start the development server, run:"
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "Or run with Python:"
echo "  python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
```

### Create `scripts/setup-venv.ps1` (for Windows PowerShell)

```powershell
Write-Host "Setting up Python virtual environment for Jira Report Service..." -ForegroundColor Green

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Copy .env.example to .env if .env doesn't exist
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created .env file from .env.example" -ForegroundColor Yellow
    Write-Host "Please edit .env with your Jira credentials" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To activate the virtual environment, run:" -ForegroundColor Cyan
Write-Host "  .venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "To start the development server, run:" -ForegroundColor Cyan
Write-Host "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
```

## Task 3: Update README.md

Add a new section after "Prerequisites":

```markdown
## Local Development Setup

### Option 1: Using Virtual Environment (Recommended)

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd jira-report
   ```

2. Run the setup script:
   - **macOS/Linux:**
     ```bash
     bash scripts/setup-venv.sh
     ```
   - **Windows (PowerShell):**
     ```powershell
     .\scripts\setup-venv.ps1
     ```

3. Edit `.env` file with your Jira credentials:
   ```bash
   # Edit .env and set your values
   JIRA_BASE_URL=https://your-domain.atlassian.net
   JIRA_EMAIL=your-email@example.com
   JIRA_API_TOKEN=your-api-token
   ```

4. Activate the virtual environment (if not already activated):
   - **macOS/Linux:** `source .venv/bin/activate`
   - **Windows:** `.venv\Scripts\Activate.ps1`

5. Start the development server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. Open http://localhost:8000 in your browser

### Option 2: Using Docker

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your credentials

# Start with docker-compose
docker-compose up -d

# Or build and run manually
docker build -t jira-report .
docker run -p 8000:8000 --env-file .env jira-report
```

### Running Tests

```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```
```

## Implementation Order

1. Create `.github/workflows/ci.yml`
2. Create `scripts/setup-venv.sh`
3. Create `scripts/setup-venv.ps1`
4. Update `README.md` with local development instructions
5. Test the setup scripts locally
6. Commit and push to verify CI workflow

## Notes

- The CI workflow runs tests on every push/PR to main branches
- Docker build only runs on pushes to main/master (not on PRs)
- Virtual environment setup scripts handle both Unix and Windows
- `.venv/` is already in `.gitignore`
- Setup scripts create `.env` from `.env.example` if it doesn't exist
