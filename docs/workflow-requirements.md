# Workflow Requirements

## GitHub Actions Testing

**Rule:** Always run tests locally for GitHub Actions workflows after pushing to GitHub.

### Implementation Notes
- After any `git push` to GitHub, execute local tests that mirror the GitHub Actions workflow
- This ensures that the code passes the same checks locally as it would in CI
- Typical test commands for this project:
  - `python -m pytest tests/` (after python alias is configured)
  - Or `python3 -m pytest tests/` if alias is not yet set

### GitHub Actions Workflow Location
- Workflows are located in `.github/` directory
- Check workflow files to understand what tests are run in CI

## System Configuration

### Python Alias Requirement
Configure system so `python` command maps to `python3`:
- Shell: zsh (default on macOS)
- Method: Add `alias python=python3` to `~/.zshrc`
- Verification: Run `python --version` to confirm it returns Python 3.x

---

*This document serves as a reminder for development workflow requirements.*
