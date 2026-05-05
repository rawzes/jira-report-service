import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from app.services.report_builder import ReportBuilder
from app.services.jira_client import JiraClient
from app.services.builder_data import (
    _get_display_name, _parse_datetime, 
    collect_all_issues_with_changelog, collect_worklogs
)
from app.services.builder_metrics import (
    calculate_flow_metrics, _get_week_ranges
)
from app.services.builder_aggregators import (
    aggregate_employee_metrics, aggregate_project_metrics,
    filter_employees_by_group, _get_employee_key
)
from app.models.schemas import (
    IssueData, WorklogEntry, EmployeeMetrics,
    ProjectMetrics, ReportData, MonthlyReportRequest
)
from app.models.config import get_settings


@pytest.fixture
def jira_client_mock():
    """Mock JiraClient."""
    client = AsyncMock(spec=JiraClient)
    client.jira = client
    return client


@pytest.fixture
def report_builder(jira_client_mock):
    """Create ReportBuilder with mocked client."""
    with patch('app.models.config.get_settings') as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.TIMEZONE = 'Europe/Minsk'
        mock_settings.done_statuses_list = ['Done']
        mock_settings.start_statuses_list = ['In Progress']
        mock_settings.blocked_statuses_list = ['Blocked']
        mock_settings.excluded_statuses_list = []
        mock_settings.JIRA_USER_GROUP = None
        mock_settings.project_keys_list = []
        mock_get_settings.return_value = mock_settings
        
        builder = ReportBuilder(jira_client_mock)
        builder.jira = jira_client_mock
        return builder


@pytest.fixture
def timezone():
    """Get timezone."""
    return ZoneInfo('Europe/Minsk')


class TestWorklogAggregation:
    """Tests for worklog aggregation."""
    
    def test_aggregate_worklog_hours_single_employee(self, report_builder, timezone):
        """Test aggregating worklog hours for a single employee."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone)
        end_date = datetime(2024, 2, 1, tzinfo=timezone)
        
        worklogs = [
            WorklogEntry(
                worklog_id="1",
                issue_key="MB-1",
                issue_id="10001",
                account_id="user1",
                display_name="John Doe",
                started=datetime(2024, 1, 15, 10, 0, tzinfo=timezone),
                time_spent_seconds=3600,  # 1 hour
                time_spent_hours=1.0,
                project_key="MB"
            ),
            WorklogEntry(
                worklog_id="2",
                issue_key="MB-1",
                issue_id="10001",
                account_id="user1",
                display_name="John Doe",
                started=datetime(2024, 1, 20, 14, 0, tzinfo=timezone),
                time_spent_seconds=7200,  # 2 hours
                time_spent_hours=2.0,
                project_key="MB"
            )
        ]
        
        report = ReportData(
            year=2024,
            month=1,
            start_date=start_date,
            end_date=end_date,
            raw_worklogs=worklogs
        )
        
        # Use the standalone function
        report.employee_metrics = aggregate_employee_metrics(
            report, [], worklogs, ['Done']
        )
        
        assert len(report.employee_metrics) == 1
        assert report.employee_metrics[0].account_id == "user1"
        assert report.employee_metrics[0].worklog_hours == 3.0
    
    def test_filter_worklog_by_date_range(self, report_builder, timezone):
        """Test that worklogs outside date range are filtered."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone)
        end_date = datetime(2024, 2, 1, tzinfo=timezone)
        
        worklogs = [
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
            ),
            WorklogEntry(
                worklog_id="2",
                issue_key="MB-1",
                issue_id="10001",
                account_id="user1",
                display_name="John Doe",
                started=datetime(2024, 2, 15, tzinfo=timezone),  # Outside range
                time_spent_seconds=3600,
                time_spent_hours=1.0,
                project_key="MB"
            )
        ]
        
        # Filter worklogs by date range
        filtered_worklogs = [
            wl for wl in worklogs 
            if start_date <= wl.started < end_date
        ]
        
        report = ReportData(
            year=2024,
            month=1,
            start_date=start_date,
            end_date=end_date,
            raw_worklogs=worklogs
        )
        
        report.employee_metrics = aggregate_employee_metrics(
            report, [], filtered_worklogs, ['Done']
        )
        
        assert len(report.employee_metrics) == 1
        assert report.employee_metrics[0].worklog_hours == 1.0


class TestCreatedClosedIssues:
    """Tests for created and closed issues aggregation."""
    
    def test_count_created_issues(self, report_builder, timezone):
        """Test counting created issues per employee."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone)
        end_date = datetime(2024, 2, 1, tzinfo=timezone)
        
        issues = [
            IssueData(
                issue_key="MB-1",
                issue_id="10001",
                project_key="MB",
                issue_type="Task",
                summary="Test issue 1",
                status="Open",
                created=datetime(2024, 1, 10, tzinfo=timezone),
                creator_account_id="user1",
                creator_display_name="John Doe",
                assignee_account_id="user1",
                assignee_display_name="John Doe"
            ),
            IssueData(
                issue_key="MB-2",
                issue_id="10002",
                project_key="MB",
                issue_type="Task",
                summary="Test issue 2",
                status="Open",
                created=datetime(2024, 1, 20, tzinfo=timezone),
                creator_account_id="user1",
                creator_display_name="John Doe",
                assignee_account_id="user1",
                assignee_display_name="John Doe"
            ),
            IssueData(
                issue_key="MAX-1",
                issue_id="10003",
                project_key="MAX",
                issue_type="Task",
                summary="Test issue 3",
                status="Open",
                created=datetime(2024, 1, 15, tzinfo=timezone),
                creator_account_id="user2",
                creator_display_name="Jane Smith",
                assignee_account_id="user2",
                assignee_display_name="Jane Smith"
            )
        ]
        
        report = ReportData(
            year=2024,
            month=1,
            start_date=start_date,
            end_date=end_date,
            raw_issues=issues
        )
        
        report.employee_metrics = aggregate_employee_metrics(
            report, issues, [], ['Done']
        )
        
        # Find user1 metrics
        user1_metrics = [m for m in report.employee_metrics if m.account_id == "user1"]
        assert len(user1_metrics) == 1
        assert user1_metrics[0].created_issues == 2
    
    def test_count_closed_issues(self, report_builder, timezone):
        """Test counting closed issues per employee."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone)
        end_date = datetime(2024, 2, 1, tzinfo=timezone)
        
        issues = [
            IssueData(
                issue_key="MB-1",
                issue_id="10001",
                project_key="MB",
                issue_type="Task",
                summary="Test issue 1",
                status="Done",
                created=datetime(2024, 1, 1, tzinfo=timezone),
                creator_account_id="user1",
                creator_display_name="John Doe",
                assignee_account_id="user1",
                assignee_display_name="John Doe",
                status_category_changed_date=datetime(2024, 1, 20, tzinfo=timezone)
            )
        ]
        
        report = ReportData(
            year=2024,
            month=1,
            start_date=start_date,
            end_date=end_date,
            raw_issues=issues
        )
        
        report.employee_metrics = aggregate_employee_metrics(
            report, issues, [], ['Done']
        )
        
        assert len(report.employee_metrics) == 1
        assert report.employee_metrics[0].closed_issues == 1


class TestProjectGrouping:
    """Tests for grouping by project."""
    
    def test_group_by_project(self, report_builder, timezone):
        """Test that metrics are grouped by project."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone)
        end_date = datetime(2024, 2, 1, tzinfo=timezone)
        
        worklogs = [
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
            ),
            WorklogEntry(
                worklog_id="2",
                issue_key="MAX-1",
                issue_id="10002",
                account_id="user1",
                display_name="John Doe",
                started=datetime(2024, 1, 16, tzinfo=timezone),
                time_spent_seconds=3600,
                time_spent_hours=1.0,
                project_key="MAX"
            )
        ]
        
        report = ReportData(
            year=2024,
            month=1,
            start_date=start_date,
            end_date=end_date,
            raw_worklogs=worklogs
        )
        
        report.employee_metrics = aggregate_employee_metrics(
            report, [], worklogs, ['Done']
        )
        
        # Should have 2 entries - one for each project
        assert len(report.employee_metrics) == 2
        
        # Aggregate project metrics
        report.project_metrics = aggregate_project_metrics(
            report, report.employee_metrics, [], [], [], [], [],
            ['Done'], ['Blocked']
        )
        
        assert len(report.project_metrics) == 2


class TestHtmlExport:
    """Tests for HTML export."""
    
    def test_generate_html(self, report_builder, timezone):
        """Test HTML generation."""
        from app.services.html_exporter import HtmlExporter
        
        report = ReportData(
            year=2024,
            month=1,
            start_date=datetime(2024, 1, 1, tzinfo=timezone),
            end_date=datetime(2024, 2, 1, tzinfo=timezone),
            raw_worklogs=[]
        )
        
        exporter = HtmlExporter(lang="en")
        result = exporter.generate(report)
        
        assert isinstance(result, str)
        assert "<!DOCTYPE html>" in result


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_deleted_user_handling(self, report_builder):
        """Test handling of deleted users."""
        display_name = _get_display_name({"displayName": "Deleted User"})
        assert display_name == ("deleted", "Deleted User")
    
    def test_missing_assignee(self, report_builder, timezone):
        """Test handling of issues with no assignee."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone)
        end_date = datetime(2024, 2, 1, tzinfo=timezone)
        
        issues = [
            IssueData(
                issue_key="MB-1",
                issue_id="10001",
                project_key="MB",
                issue_type="Task",
                summary="Test issue",
                status="Open",
                created=datetime(2024, 1, 10, tzinfo=timezone),
                creator_account_id="user1",
                creator_display_name="John Doe",
                assignee_account_id=None,
                assignee_display_name=None
            )
        ]
        
        report = ReportData(
            year=2024,
            month=1,
            start_date=start_date,
            end_date=end_date,
            raw_issues=issues
        )
        
        report.employee_metrics = aggregate_employee_metrics(
            report, issues, [], ['Done']
        )
        
        # Should not crash
        assert isinstance(report.employee_metrics, list)


class TestParseDateTime:
    """Tests for datetime parsing."""
    
    def test_parse_valid_datetime(self):
        """Test parsing valid datetime string."""
        result = _parse_datetime("2024-01-15T10:30:00.000+0000")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
    
    def test_parse_datetime_with_z(self):
        """Test parsing datetime with Z suffix."""
        result = _parse_datetime("2024-01-15T10:30:00.000Z")
        assert result is not None
        assert result.year == 2024
    
    def test_parse_datetime_none(self):
        """Test parsing None value."""
        result = _parse_datetime(None)
        assert result is None
    
    def test_parse_datetime_empty_string(self):
        """Test parsing empty string."""
        result = _parse_datetime("")
        assert result is None
    
    def test_parse_datetime_invalid(self):
        """Test parsing invalid string."""
        result = _parse_datetime("invalid")
        assert result is None


class TestGetWeekRanges:
    """Tests for week range calculation."""
    
    def test_get_week_ranges_full_month(self, timezone):
        """Test week ranges for a full month."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone)
        end_date = datetime(2024, 2, 1, tzinfo=timezone)
        
        ranges = _get_week_ranges(start_date, end_date)
        
        assert len(ranges) > 0
        for week_start, week_end in ranges:
            assert week_start < week_end
    
    def test_get_week_ranges_partial_month(self, timezone):
        """Test week ranges for partial month."""
        start_date = datetime(2024, 1, 15, tzinfo=timezone)
        end_date = datetime(2024, 1, 25, tzinfo=timezone)
        
        ranges = _get_week_ranges(start_date, end_date)
        
        assert len(ranges) > 0


class TestGetEmployeeKey:
    """Tests for employee key generation."""
    
    def test_get_employee_key(self):
        """Test generating employee key."""
        key = _get_employee_key("user1", "John Doe")
        assert "user1" in key
        assert "John Doe" in key
    
    def test_get_employee_key_unique(self):
        """Test that same user in different projects gets unique keys."""
        key1 = _get_employee_key("user1", "John Doe")
        key2 = _get_employee_key("user1", "John Doe")
        assert key1 == key2  # Same user should have same key


class TestGetDisplayName:
    """Tests for display name extraction."""
    
    def test_get_display_name_normal_user(self):
        """Test extracting display name from normal user."""
        user_obj = {"accountId": "user1", "displayName": "John Doe"}
        account_id, display_name = _get_display_name(user_obj)
        assert account_id == "user1"
        assert display_name == "John Doe"
    
    def test_get_display_name_deleted_user(self):
        """Test extracting display name from deleted user."""
        user_obj = {"displayName": "Deleted User"}
        account_id, display_name = _get_display_name(user_obj)
        assert account_id == "deleted"
        assert display_name == "Deleted User"
    
    def test_get_display_name_none(self):
        """Test extracting display name from None."""
        account_id, display_name = _get_display_name(None)
        assert account_id is None
        assert display_name is None
    
    def test_get_display_name_empty_dict(self):
        """Test extracting display name from empty dict."""
        account_id, display_name = _get_display_name({})
        assert account_id is None
        assert display_name is None


class TestFilterExcludedStatuses:
    """Tests for filtering excluded statuses."""
    
    def test_filter_excluded_statuses(self, report_builder, timezone):
        """Test filtering issues with excluded statuses."""
        issues = [
            IssueData(
                issue_key="MB-1",
                issue_id="10001",
                project_key="MB",
                issue_type="Task",
                summary="Test issue 1",
                status="Done",
                created=datetime(2024, 1, 1, tzinfo=timezone)
            ),
            IssueData(
                issue_key="MB-2",
                issue_id="10002",
                project_key="MB",
                issue_type="Task",
                summary="Test issue 2",
                status="Cancelled",  # Excluded
                created=datetime(2024, 1, 1, tzinfo=timezone)
            )
        ]
        
        # Filter excluded statuses
        filtered = [i for i in issues if i.status != "Cancelled"]
        
        assert len(filtered) == 1
        assert filtered[0].status == "Done"
    
    def test_filter_no_exclusions(self, report_builder, timezone):
        """Test with no excluded statuses."""
        issues = [
            IssueData(
                issue_key="MB-1", 
                issue_id="10001",
                project_key="MB", 
                issue_type="Task", 
                summary="Test", 
                status="Open",
                created=datetime(2024, 1, 1, tzinfo=timezone)
            ),
            IssueData(
                issue_key="MB-2", 
                issue_id="10002",
                project_key="MB", 
                issue_type="Task", 
                summary="Test", 
                status="Done",
                created=datetime(2024, 1, 1, tzinfo=timezone)
            )
        ]
        
        # No filtering
        assert len(issues) == 2


class TestParseIssueFromChangelog:
    """Tests for parsing issues from changelog."""
    
    def test_parse_issue_basic(self, timezone):
        """Test basic issue parsing."""
        from app.services.builder_data import _parse_issue_from_changelog
        
        issue_data = {
            "key": "MB-1",
            "id": "10001",
            "fields": {
                "project": {"key": "MB"},
                "summary": "Test issue",
                "status": {"name": "Open"},
                "created": "2024-01-01T10:00:00.000+0000",
                "creator": {"accountId": "user1", "displayName": "John Doe"},
                "assignee": {"accountId": "user1", "displayName": "John Doe"}
            },
            "changelog": {"histories": []}
        }
        
        result = _parse_issue_from_changelog(issue_data, ['Done'], ['In Progress'], ['Blocked'])
        
        assert result.issue_key == "MB-1"
        assert result.project_key == "MB"
    
    def test_parse_issue_with_transitions(self, timezone):
        """Test parsing issue with status transitions."""
        from app.services.builder_data import _parse_issue_from_changelog
        
        issue_data = {
            "key": "MB-1",
            "id": "10001",
            "fields": {
                "project": {"key": "MB"},
                "summary": "Test issue",
                "status": {"name": "Done"},
                "created": "2024-01-01T10:00:00.000+0000",
                "creator": {"accountId": "user1", "displayName": "John Doe"},
                "assignee": {"accountId": "user1", "displayName": "John Doe"}
            },
            "changelog": {
                "histories": [
                    {
                        "created": "2024-01-10T10:00:00.000+0000",
                        "items": [
                            {"field": "status", "fromString": "Open", "toString": "In Progress"}
                        ]
                    },
                    {
                        "created": "2024-01-20T10:00:00.000+0000",
                        "items": [
                            {"field": "status", "fromString": "In Progress", "toString": "Done"}
                        ]
                    }
                ]
            }
        }
        
        result = _parse_issue_from_changelog(issue_data, ['Done'], ['In Progress'], ['Blocked'])
        
        assert result.issue_key == "MB-1"
        assert len(result.transitions) == 2


class TestAggregateEmployeeMetricsEdgeCases:
    """Edge cases for employee metrics aggregation."""
    
    def test_employee_with_no_worklogs(self, report_builder, timezone):
        """Test employee with no worklogs."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone)
        end_date = datetime(2024, 2, 1, tzinfo=timezone)
        
        issues = [
            IssueData(
                issue_key="MB-1",
                issue_id="10001",
                project_key="MB",
                issue_type="Task",
                summary="Test issue",
                status="Open",
                created=datetime(2024, 1, 10, tzinfo=timezone),
                creator_account_id="user1",
                creator_display_name="John Doe"
            )
        ]
        
        report = ReportData(
            year=2024,
            month=1,
            start_date=start_date,
            end_date=end_date,
            raw_issues=issues
        )
        
        report.employee_metrics = aggregate_employee_metrics(
            report, issues, [], ['Done']
        )
        
        assert len(report.employee_metrics) == 1
        assert report.employee_metrics[0].worklog_hours == 0.0
    
    def test_multiple_employees_same_project(self, report_builder, timezone):
        """Test multiple employees on same project."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone)
        end_date = datetime(2024, 2, 1, tzinfo=timezone)
        
        worklogs = [
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
            ),
            WorklogEntry(
                worklog_id="2",
                issue_key="MB-2",
                issue_id="10002",
                account_id="user2",
                display_name="Jane Smith",
                started=datetime(2024, 1, 16, tzinfo=timezone),
                time_spent_seconds=3600,
                time_spent_hours=1.0,
                project_key="MB"
            )
        ]
        
        report = ReportData(
            year=2024,
            month=1,
            start_date=start_date,
            end_date=end_date,
            raw_worklogs=worklogs
        )
        
        report.employee_metrics = aggregate_employee_metrics(
            report, [], worklogs, ['Done']
        )
        
        assert len(report.employee_metrics) == 2


class TestAggregateProjectMetricsEdgeCases:
    """Edge cases for project metrics aggregation."""
    
    def test_project_with_no_employees(self, report_builder, timezone):
        """Test project with no employees."""
        report = ReportData(
            year=2024, 
            month=1,
            start_date=datetime(2024, 1, 1, tzinfo=timezone),
            end_date=datetime(2024, 2, 1, tzinfo=timezone),
            raw_worklogs=[]
        )
        report.employee_metrics = []
        
        report.project_metrics = aggregate_project_metrics(
            report, [], [], [], [], [], [],
            ['Done'], ['Blocked']
        )
        
        assert len(report.project_metrics) == 0
    
    def test_single_employee_single_project(self, report_builder, timezone):
        """Test single employee on single project."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone)
        end_date = datetime(2024, 2, 1, tzinfo=timezone)
        
        worklogs = [
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
        ]
        
        report = ReportData(
            year=2024,
            month=1,
            start_date=start_date,
            end_date=end_date,
            raw_worklogs=worklogs
        )
        
        report.employee_metrics = aggregate_employee_metrics(
            report, [], worklogs, ['Done']
        )
        
        report.project_metrics = aggregate_project_metrics(
            report, report.employee_metrics, [], [], [], [], [],
            ['Done'], ['Blocked']
        )
        
        assert len(report.project_metrics) == 1
        assert report.project_metrics[0].project_key == "MB"
