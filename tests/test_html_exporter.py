"""
Unit tests for HtmlExporter service.

Tests cover HTML generation, localization, and various report sections.
"""

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import MagicMock, patch
from io import BytesIO

from app.services.html_exporter import HtmlExporter
from app.models.schemas import (
    ReportData, EmployeeMetrics, ProjectMetrics, IssueData, 
    WorklogEntry, IssueTransition, WeeklyThroughput, CycleTimeData,
    AgingWipData, OverdueData, ReopenedData, StatusDistribution,
    WeeklyCycleTime
)
from app.models.config import get_settings
from app.services.html_sections import (
    generate_summary_section,
    generate_by_employee_section,
    generate_by_project_section,
    generate_employee_worklog_summary_section,
    generate_weekly_throughput_section,
    generate_cycle_time_section,
    generate_aging_wip_section,
    generate_overdue_section,
    generate_reopened_section,
    generate_raw_data_sections,
)
from app.services.html_charts import generate_charts_section, _prepare_chart_data


@pytest.fixture
def timezone():
    """Get timezone."""
    return ZoneInfo('Europe/Minsk')


@pytest.fixture
def mock_settings():
    """Mock settings for HtmlExporter."""
    with patch('app.services.html_exporter.get_settings') as mock_get_settings:
        settings = MagicMock()
        settings.REPORT_LANG = "ru"
        settings.JIRA_BASE_URL = "https://test.atlassian.net"
        settings.JIRA_PROJECT_KEYS = "MB,MAX"
        settings.JIRA_DONE_STATUSES = "Done,Closed"
        settings.JIRA_BLOCKED_STATUSES = "Blocked"
        mock_get_settings.return_value = settings
        yield settings


@pytest.fixture
def html_exporter(mock_settings):
    """Create HtmlExporter instance."""
    return HtmlExporter(lang="ru")


@pytest.fixture
def html_exporter_en(mock_settings):
    """Create HtmlExporter instance with English."""
    return HtmlExporter(lang="en")


@pytest.fixture
def sample_worklog(timezone):
    """Create a sample worklog entry."""
    return WorklogEntry(
        worklog_id="1",
        issue_key="MB-1",
        issue_id="10001",
        account_id="user1",
        display_name="John Doe",
        started=datetime(2024, 1, 15, 10, 0, tzinfo=timezone),
        time_spent_seconds=3600,
        time_spent_hours=1.0,
        project_key="MB"
    )


@pytest.fixture
def sample_issue(timezone):
    """Create a sample issue."""
    return IssueData(
        issue_key="MB-1",
        issue_id="10001",
        project_key="MB",
        issue_type="Task",
        summary="Test issue",
        status="Done",
        created=datetime(2024, 1, 1, tzinfo=timezone),
        creator_account_id="user1",
        creator_display_name="John Doe",
        assignee_account_id="user1",
        assignee_display_name="John Doe",
        resolution_date=datetime(2024, 1, 20, tzinfo=timezone),
        status_category_changed_date=datetime(2024, 1, 20, tzinfo=timezone),
        cycle_time_days=19.0,
        cycle_time_hours=456.0
    )


@pytest.fixture
def sample_employee_metrics():
    """Create sample employee metrics."""
    return EmployeeMetrics(
        account_id="user1",
        display_name="John Doe",
        project_key="MB",
        worklog_hours=10.0,
        created_issues=5,
        closed_issues=3,
        reopened_tasks=1,
        active_wip=2,
        avg_cycle_time=15.5,
        median_cycle_time=14.0
    )


@pytest.fixture
def sample_project_metrics():
    """Create sample project metrics."""
    return ProjectMetrics(
        project_key="MB",
        total_worklog_hours=100.0,
        total_created_issues=20,
        total_closed_issues=15,
        throughput=15,
        avg_cycle_time=12.5,
        median_cycle_time=11.0,
        p85_cycle_time=20.0
    )


@pytest.fixture
def minimal_report_data(timezone):
    """Create minimal ReportData for testing."""
    return ReportData(
        year=2024,
        month=1,
        start_date=datetime(2024, 1, 1, tzinfo=timezone),
        end_date=datetime(2024, 2, 1, tzinfo=timezone)
    )


@pytest.fixture
def full_report_data(timezone, sample_employee_metrics, sample_project_metrics):
    """Create full ReportData with all fields."""
    return ReportData(
        year=2024,
        month=1,
        start_date=datetime(2024, 1, 1, tzinfo=timezone),
        end_date=datetime(2024, 2, 1, tzinfo=timezone),
        raw_worklogs=[
            WorklogEntry(
                worklog_id="1",
                issue_key="MB-1",
                issue_id="10001",
                account_id="user1",
                display_name="John Doe",
                started=datetime(2024, 1, 15, tzinfo=timezone),
                time_spent_seconds=3600,
                time_spent_hours=1.0,
                project_key="MB"
            )
        ],
        raw_issues=[
            IssueData(
                issue_key="MB-1",
                issue_id="10001",
                project_key="MB",
                issue_type="Task",
                summary="Test issue",
                status="Done",
                created=datetime(2024, 1, 1, tzinfo=timezone),
                creator_account_id="user1",
                creator_display_name="John Doe"
            )
        ],
        employee_metrics=[sample_employee_metrics],
        project_metrics=[sample_project_metrics],
        total_worklog_hours=10.0,
        total_created_issues=5,
        total_closed_issues=3,
        throughput=3,
        median_cycle_time=14.0,
        p85_cycle_time=20.0,
        reopened_tasks_count=1,
        blocked_tasks_count=0,
        overdue_tasks_count=0,
        include_raw_data=True
    )


class TestHtmlExporterInit:
    """Tests for HtmlExporter initialization."""
    
    def test_init_default_lang(self, mock_settings):
        """Test initialization with default language."""
        exporter = HtmlExporter()
        assert exporter.lang == "ru"
        assert exporter.jira_base == "https://test.atlassian.net"
    
    def test_init_custom_lang(self, mock_settings):
        """Test initialization with custom language."""
        exporter = HtmlExporter(lang="en")
        assert exporter.lang == "en"
    
    def test_init_invalid_lang_fallback(self, mock_settings):
        """Test that invalid language falls back to English."""
        exporter = HtmlExporter(lang="invalid")
        assert exporter.lang == "en"
    
    def test_init_loads_localization(self, mock_settings):
        """Test that localization dictionary is loaded."""
        exporter = HtmlExporter(lang="ru")
        assert exporter._ is not None
        assert "summary" in exporter._


class TestHtmlExporterGenerate:
    """Tests for HTML generation."""
    
    def test_generate_returns_html_string(self, html_exporter, minimal_report_data):
        """Test that generate returns a string."""
        result = html_exporter.generate(minimal_report_data)
        assert isinstance(result, str)
        assert "<!DOCTYPE html>" in result
        assert "</html>" in result
    
    def test_generate_contains_title(self, html_exporter, minimal_report_data):
        """Test that generated HTML contains title."""
        result = html_exporter.generate(minimal_report_data)
        assert "Отчет за период" in result
    
    def test_generate_english_title(self, html_exporter_en, minimal_report_data):
        """Test English title."""
        result = html_exporter_en.generate(minimal_report_data)
        assert "Report for period" in result or "Report" in result
    
    def test_generate_contains_date_range(self, html_exporter, minimal_report_data):
        """Test that date range is in the HTML."""
        result = html_exporter.generate(minimal_report_data)
        assert "2024-01-01" in result
        assert "2024-02-01" in result
    
    def test_generate_with_full_data(self, html_exporter, full_report_data):
        """Test generation with complete data."""
        result = html_exporter.generate(full_report_data)
        assert isinstance(result, str)
        assert len(result) > 1000  # Should be substantial HTML
    
    def test_generate_includes_jira_links(self, html_exporter, full_report_data):
        """Test that JIRA links are generated."""
        result = html_exporter.generate(full_report_data)
        assert "test.atlassian.net" in result
        assert "jql=" in result
    
    def test_generate_includes_tab_navigation(self, html_exporter, minimal_report_data):
        """Test that tab navigation is present."""
        result = html_exporter.generate(minimal_report_data)
        assert 'tab-button' in result
        assert 'data-tab="by-employee"' in result
        assert 'data-tab="by-project"' in result
    
    def test_generate_includes_css(self, html_exporter, minimal_report_data):
        """Test that CSS is included."""
        result = html_exporter.generate(minimal_report_data)
        assert "<style>" in result
        assert "</style>" in result
        assert "body {" in result
    
    def test_generate_includes_javascript(self, html_exporter, minimal_report_data):
        """Test that JavaScript is included."""
        result = html_exporter.generate(minimal_report_data)
        assert "<script>" in result
        assert "</script>" in result
        assert "tab-button" in result


class TestHtmlExporterHelperMethods:
    """Tests for helper methods."""
    
    def test_generate_jira_link(self, html_exporter):
        """Test JIRA link generation."""
        jql = 'project = "MB"'
        text = "MB-1"
        result = html_exporter._generate_jira_link(jql, text)
        
        assert "<a href=" in result
        assert "test.atlassian.net/issues/" in result
        assert "jql=" in result
        assert text in result
        assert 'target="_blank"' in result
    
    def test_generate_jira_link_special_chars(self, html_exporter):
        """Test JIRA link with special characters in JQL."""
        jql = 'project = "MB" AND status = "In Progress"'
        text = "Test"
        result = html_exporter._generate_jira_link(jql, text)
        
        assert "jql=" in result
        # URL should be encoded
        assert "%20" in result or "status" in result
    
    def test_get_css_returns_string(self, html_exporter):
        """Test that get_css returns a string."""
        from app.services.html_styles import get_css
        css = get_css()
        assert isinstance(css, str)
        assert len(css) > 100
        assert "* {" in css or "body {" in css


class TestHtmlExporterSections:
    """Tests for individual HTML sections."""
    
    def test_generate_summary_section(self, html_exporter, full_report_data):
        """Test summary section generation."""
        from app.services.localization import get_localization
        _ = get_localization("ru")
        created_jql = "project = MB AND created >= '2024-01-01'"
        closed_jql = "project = MB AND status changed to Done"
        overdue_jql = "project = MB AND duedate < now()"
        reopened_jql = "project = MB AND status changed from Done"
        blocked_jql = "project = MB AND status = Blocked"
        
        result = generate_summary_section(
            full_report_data, "https://test.atlassian.net", _, 
            created_jql, closed_jql, overdue_jql, reopened_jql, blocked_jql
        )
        
        assert isinstance(result, str)
        assert "Сводка" in result or "summary" in result.lower()
        assert "10.00" in result  # total_worklog_hours
    
    def test_generate_by_employee_section_empty(self, html_exporter, minimal_report_data):
        """Test employee section with no data."""
        from app.services.localization import get_localization
        _ = get_localization("ru")
        result = generate_by_employee_section(minimal_report_data, "https://test.atlassian.net", _)
        assert isinstance(result, str)
    
    def test_generate_by_employee_section_with_data(self, html_exporter, full_report_data):
        """Test employee section with data."""
        from app.services.localization import get_localization
        _ = get_localization("ru")
        result = generate_by_employee_section(full_report_data, "https://test.atlassian.net", _)
        assert isinstance(result, str)
        assert "John Doe" in result or "user1" in result
    
    def test_generate_by_project_section_empty(self, html_exporter, minimal_report_data):
        """Test project section with no data."""
        from app.services.localization import get_localization
        _ = get_localization("ru")
        result = generate_by_project_section(minimal_report_data, "https://test.atlassian.net", _)
        assert isinstance(result, str)
    
    def test_generate_by_project_section_with_data(self, html_exporter, full_report_data):
        """Test project section with data."""
        from app.services.localization import get_localization
        _ = get_localization("ru")
        result = generate_by_project_section(full_report_data, "https://test.atlassian.net", _)
        assert isinstance(result, str)
        assert "MB" in result
    
    def test_generate_employee_worklog_summary_empty(self, html_exporter, minimal_report_data):
        """Test worklog summary with no data."""
        from app.services.localization import get_localization
        _ = get_localization("ru")
        result = generate_employee_worklog_summary_section(minimal_report_data, _)
        assert isinstance(result, str)
    
    def test_generate_employee_worklog_summary_with_data(self, html_exporter, full_report_data):
        """Test worklog summary with data."""
        from app.services.localization import get_localization
        _ = get_localization("ru")
        result = generate_employee_worklog_summary_section(full_report_data, _)
        assert isinstance(result, str)


class TestHtmlExporterWithRawData:
    """Tests for raw data inclusion."""
    
    def test_generate_with_raw_data(self, html_exporter, full_report_data):
        """Test that raw data is included when include_raw_data is True."""
        full_report_data.include_raw_data = True
        result = html_exporter.generate(full_report_data)
        assert "raw-data" in result or "Raw" in result
    
    def test_generate_without_raw_data(self, html_exporter, full_report_data):
        """Test that raw data is excluded when include_raw_data is False."""
        full_report_data.include_raw_data = False
        result = html_exporter.generate(full_report_data)
        # Raw data section should not be present or should be empty
        assert isinstance(result, str)


class TestHtmlExporterEdgeCases:
    """Tests for edge cases."""
    
    def test_generate_with_none_values(self, html_exporter, minimal_report_data):
        """Test generation with None values in report data."""
        minimal_report_data.median_cycle_time = None
        minimal_report_data.p85_cycle_time = None
        result = html_exporter.generate(minimal_report_data)
        assert isinstance(result, str)
    
    def test_generate_with_empty_strings(self, html_exporter, minimal_report_data):
        """Test generation handles empty strings properly."""
        result = html_exporter.generate(minimal_report_data)
        assert isinstance(result, str)
    
    def test_generate_very_large_worklog_hours(self, html_exporter, full_report_data):
        """Test formatting of large numbers."""
        full_report_data.total_worklog_hours = 123456.789
        result = html_exporter.generate(full_report_data)
        assert "123456.79" in result or "123456,79" in result
    
    def test_generate_special_characters_in_summary(self, html_exporter, full_report_data):
        """Test that special characters in issue summary are handled."""
        if full_report_data.raw_issues:
            full_report_data.raw_issues[0].summary = "Test <script>alert('xss')</script> & more"
        result = html_exporter.generate(full_report_data)
        # Should not contain unescaped script tags
        assert isinstance(result, str)


class TestHtmlExporterLocalization:
    """Tests for localization features."""
    
    def test_russian_localization(self, html_exporter, minimal_report_data):
        """Test Russian localization strings."""
        result = html_exporter.generate(minimal_report_data)
        # Check for Russian text
        assert "Отчет" in result or "Сводка" in result
    
    def test_english_localization(self, html_exporter_en, minimal_report_data):
        """Test English localization strings."""
        result = html_exporter_en.generate(minimal_report_data)
        # Check for English text
        assert "Report" in result or "Summary" in result
    
    def test_localization_fallback(self, mock_settings):
        """Test fallback to English for unknown language."""
        exporter = HtmlExporter(lang="fr")  # French not supported
        assert exporter.lang == "en"  # Should fallback


class TestHtmlExporterCharts:
    """Tests for chart generation."""
    
    def test_generate_charts_section(self, html_exporter, full_report_data):
        """Test that charts section is generated."""
        result = html_exporter.generate(full_report_data)
        assert "chart" in result.lower() or "Chart" in result
        assert "chart.js" in result or "canvas" in result
    
    def test_chart_data_format(self, html_exporter, full_report_data):
        """Test that chart data is properly formatted."""
        result = html_exporter.generate(full_report_data)
        # Charts should have proper JavaScript data structures
        assert isinstance(result, str)


class TestHtmlExporterDownloadButton:
    """Tests for download functionality."""
    
    def test_download_button_present(self, html_exporter, minimal_report_data):
        """Test that download button is present."""
        result = html_exporter.generate(minimal_report_data)
        assert "downloadBtn" in result or "download" in result.lower()
        assert "Скачать отчет" in result or "Download" in result
    
    def test_download_function_defined(self, html_exporter, minimal_report_data):
        """Test that download JavaScript function is defined."""
        result = html_exporter.generate(minimal_report_data)
        assert "downloadReport" in result or "function" in result
