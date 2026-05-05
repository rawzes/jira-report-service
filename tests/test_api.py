"""
Unit tests for API endpoints.
Tests cover report generation endpoints, request parsing, and response formats.
"""

import pytest
from datetime import date, datetime
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from fastapi.testclient import TestClient
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from app.main import app
from app.models.schemas import MonthlyReportRequest, CustomReportRequest, ReportData
from app.models.config import get_settings


# Create test client
client = TestClient(app)


@pytest.fixture
def mock_report_data():
    """Create mock ReportData for testing."""
    timezone = ZoneInfo('Europe/Minsk')
    return ReportData(
        year=2024,
        month=1,
        start_date=datetime(2024, 1, 1, tzinfo=timezone),
        end_date=datetime(2024, 2, 1, tzinfo=timezone),
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


@pytest.fixture
def mock_settings():
    """Mock settings for API tests."""
    with patch('app.api.report.get_settings') as mock_get_settings:
        with patch('app.services.report_builder.get_settings') as mock_rb_settings:
            with patch('app.services.html_exporter.get_settings') as mock_html_settings:
                settings = MagicMock()
                settings.JIRA_BASE_URL = "https://test.atlassian.net"
                settings.JIRA_PROJECT_KEYS = "MB,MAX"
                settings.JIRA_DONE_STATUSES = "Done,Closed"
                settings.JIRA_BLOCKED_STATUSES = "Blocked"
                settings.REPORT_LANG = "ru"
                
                mock_get_settings.return_value = settings
                mock_rb_settings.return_value = settings
                mock_html_settings.return_value = settings
                
                yield settings


class TestMonthlyReportGetEndpoint:
    """Tests for GET /reports/monthly endpoint."""

    @patch('app.api.report.ReportBuilder')
    @patch('app.api.report.JiraClient')
    def test_monthly_get_html_response(self, mock_jira_client, mock_report_builder, mock_settings, mock_report_data):
        """Test monthly report GET returns HTML by default."""
        # Setup mocks
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build_report.return_value = mock_report_data
        mock_report_builder.return_value = mock_builder_instance
        
        mock_jira_instance = AsyncMock()
        mock_jira_client.return_value.__aenter__ = AsyncMock(return_value=mock_jira_instance)
        mock_jira_client.return_value.__aexit__ = AsyncMock(return_value=False)
        
        with patch('app.api.report.HtmlExporter') as mock_html_exporter:
            mock_exporter_instance = MagicMock()
            mock_exporter_instance.generate.return_value = "<html>Test Report</html>"
            mock_html_exporter.return_value = mock_exporter_instance
            
            response = client.get("/reports/monthly?year=2024&month=1")
            
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")

    @patch('app.api.report.ReportBuilder')
    @patch('app.api.report.JiraClient')
    def test_monthly_get_json_response(self, mock_jira_client, mock_report_builder, mock_settings, mock_report_data):
        """Test monthly report GET with JSON format."""
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build_report.return_value = mock_report_data
        mock_report_builder.return_value = mock_builder_instance
        
        mock_jira_instance = AsyncMock()
        mock_jira_client.return_value.__aenter__ = AsyncMock(return_value=mock_jira_instance)
        mock_jira_client.return_value.__aexit__ = AsyncMock(return_value=False)
        
        response = client.get("/reports/monthly?year=2024&month=1&format=json")
        
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    @patch('app.api.report.ReportBuilder')
    @patch('app.api.report.JiraClient')
    def test_monthly_get_htmldownload_response(self, mock_jira_client, mock_report_builder, mock_settings, mock_report_data):
        """Test monthly report GET with htmldownload format."""
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build_report.return_value = mock_report_data
        mock_report_builder.return_value = mock_builder_instance
        
        mock_jira_instance = AsyncMock()
        mock_jira_client.return_value.__aenter__ = AsyncMock(return_value=mock_jira_instance)
        mock_jira_client.return_value.__aexit__ = AsyncMock(return_value=False)
        
        with patch('app.api.report.HtmlExporter') as mock_html_exporter:
            mock_exporter_instance = MagicMock()
            mock_exporter_instance.generate.return_value = "<html>Test Report</html>"
            mock_html_exporter.return_value = mock_exporter_instance
            
            response = client.get("/reports/monthly?year=2024&month=1&format=htmldownload")
            
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
            assert "attachment" in response.headers.get("content-disposition", "")

    def test_monthly_get_missing_params(self):
        """Test monthly report GET with missing parameters."""
        response = client.get("/reports/monthly")
        # Should return 422 for missing required params
        assert response.status_code == 422

    @patch('app.api.report.ReportBuilder')
    @patch('app.api.report.JiraClient')
    def test_monthly_get_with_project_keys(self, mock_jira_client, mock_report_builder, mock_settings, mock_report_data):
        """Test monthly report GET with project_keys parameter."""
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build_report.return_value = mock_report_data
        mock_report_builder.return_value = mock_builder_instance
        
        mock_jira_instance = AsyncMock()
        mock_jira_client.return_value.__aenter__ = AsyncMock(return_value=mock_jira_instance)
        mock_jira_client.return_value.__aexit__ = AsyncMock(return_value=False)
        
        with patch('app.api.report.HtmlExporter') as mock_html_exporter:
            mock_exporter_instance = MagicMock()
            mock_exporter_instance.generate.return_value = "<html>Test</html>"
            mock_html_exporter.return_value = mock_exporter_instance
            
            response = client.get("/reports/monthly?year=2024&month=1&project_keys=MB,MAX")
            
            assert response.status_code == 200
            # Verify the request was made with parsed project keys
            call_args = mock_report_builder.return_value.build_report.call_args
            assert call_args is not None

    @patch('app.api.report.ReportBuilder')
    @patch('app.api.report.JiraClient')
    def test_monthly_get_with_group(self, mock_jira_client, mock_report_builder, mock_settings, mock_report_data):
        """Test monthly report GET with group parameter."""
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build_report.return_value = mock_report_data
        mock_report_builder.return_value = mock_builder_instance
        
        mock_jira_instance = AsyncMock()
        mock_jira_client.return_value.__aenter__ = AsyncMock(return_value=mock_jira_instance)
        mock_jira_client.return_value.__aexit__ = AsyncMock(return_value=False)
        
        with patch('app.api.report.HtmlExporter') as mock_html_exporter:
            mock_exporter_instance = MagicMock()
            mock_exporter_instance.generate.return_value = "<html>Test</html>"
            mock_html_exporter.return_value = mock_exporter_instance
            
            response = client.get("/reports/monthly?year=2024&month=1&group=IT")
            
            assert response.status_code == 200

    @patch('app.api.report.ReportBuilder')
    @patch('app.api.report.JiraClient')
    def test_monthly_get_with_lang(self, mock_jira_client, mock_report_builder, mock_settings, mock_report_data):
        """Test monthly report GET with language parameter."""
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build_report.return_value = mock_report_data
        mock_report_builder.return_value = mock_builder_instance
        
        mock_jira_instance = AsyncMock()
        mock_jira_client.return_value.__aenter__ = AsyncMock(return_value=mock_jira_instance)
        mock_jira_client.return_value.__aexit__ = AsyncMock(return_value=False)
        
        with patch('app.api.report.HtmlExporter') as mock_html_exporter:
            mock_exporter_instance = MagicMock()
            mock_exporter_instance.generate.return_value = "<html>Test</html>"
            mock_html_exporter.return_value = mock_exporter_instance
            
            response = client.get("/reports/monthly?year=2024&month=1&lang=en")
            
            assert response.status_code == 200


class TestMonthlyReportPostEndpoint:
    """Tests for POST /reports/monthly endpoint."""

    @patch('app.api.report.ReportBuilder')
    @patch('app.api.report.JiraClient')
    def test_monthly_post_html_response(self, mock_jira_client, mock_report_builder, mock_settings, mock_report_data):
        """Test monthly report POST returns HTML by default."""
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build_report.return_value = mock_report_data
        mock_report_builder.return_value = mock_builder_instance
        
        mock_jira_instance = AsyncMock()
        mock_jira_client.return_value.__aenter__ = AsyncMock(return_value=mock_jira_instance)
        mock_jira_client.return_value.__aexit__ = AsyncMock(return_value=False)
        
        with patch('app.api.report.HtmlExporter') as mock_html_exporter:
            mock_exporter_instance = MagicMock()
            mock_exporter_instance.generate.return_value = "<html>Test Report</html>"
            mock_html_exporter.return_value = mock_exporter_instance
            
            response = client.post(
                "/reports/monthly",
                json={"year": 2024, "month": 1}
            )
            
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")

    @patch('app.api.report.ReportBuilder')
    @patch('app.api.report.JiraClient')
    def test_monthly_post_json_response(self, mock_jira_client, mock_report_builder, mock_settings, mock_report_data):
        """Test monthly report POST with JSON format."""
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build_report.return_value = mock_report_data
        mock_report_builder.return_value = mock_builder_instance
        
        mock_jira_instance = AsyncMock()
        mock_jira_client.return_value.__aenter__ = AsyncMock(return_value=mock_jira_instance)
        mock_jira_client.return_value.__aexit__ = AsyncMock(return_value=False)
        
        response = client.post(
            "/reports/monthly?format=json",
            json={"year": 2024, "month": 1}
        )
        
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_monthly_post_invalid_data(self):
        """Test monthly report POST with invalid data."""
        response = client.post(
            "/reports/monthly",
            json={"year": "invalid", "month": 1}
        )
        assert response.status_code == 422


class TestCustomReportGetEndpoint:
    """Tests for GET /reports/custom endpoint."""

    @patch('app.api.report.ReportBuilder')
    @patch('app.api.report.JiraClient')
    def test_custom_get_html_response(self, mock_jira_client, mock_report_builder, mock_settings, mock_report_data):
        """Test custom report GET returns HTML by default."""
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build_custom_report.return_value = mock_report_data
        mock_report_builder.return_value = mock_builder_instance
        
        mock_jira_instance = AsyncMock()
        mock_jira_client.return_value.__aenter__ = AsyncMock(return_value=mock_jira_instance)
        mock_jira_client.return_value.__aexit__ = AsyncMock(return_value=False)
        
        with patch('app.api.report.HtmlExporter') as mock_html_exporter:
            mock_exporter_instance = MagicMock()
            mock_exporter_instance.generate.return_value = "<html>Test Report</html>"
            mock_html_exporter.return_value = mock_exporter_instance
            
            response = client.get("/reports/custom?start_date=2024-01-01&end_date=2024-01-31")
            
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")

    @patch('app.api.report.ReportBuilder')
    @patch('app.api.report.JiraClient')
    def test_custom_get_json_response(self, mock_jira_client, mock_report_builder, mock_settings, mock_report_data):
        """Test custom report GET with JSON format."""
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build_custom_report.return_value = mock_report_data
        mock_report_builder.return_value = mock_builder_instance
        
        mock_jira_instance = AsyncMock()
        mock_jira_client.return_value.__aenter__ = AsyncMock(return_value=mock_jira_instance)
        mock_jira_client.return_value.__aexit__ = AsyncMock(return_value=False)
        
        response = client.get("/reports/custom?start_date=2024-01-01&end_date=2024-01-31&format=json")
        
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_custom_get_missing_params(self):
        """Test custom report GET with missing parameters."""
        response = client.get("/reports/custom")
        assert response.status_code == 422

    def test_custom_get_invalid_date_format(self):
        """Test custom report GET with invalid date format."""
        response = client.get("/reports/custom?start_date=invalid&end_date=2024-01-31")
        assert response.status_code == 422


class TestCustomReportPostEndpoint:
    """Tests for POST /reports/custom endpoint."""

    @patch('app.api.report.ReportBuilder')
    @patch('app.api.report.JiraClient')
    def test_custom_post_html_response(self, mock_jira_client, mock_report_builder, mock_settings, mock_report_data):
        """Test custom report POST returns HTML by default."""
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build_custom_report.return_value = mock_report_data
        mock_report_builder.return_value = mock_builder_instance
        
        mock_jira_instance = AsyncMock()
        mock_jira_client.return_value.__aenter__ = AsyncMock(return_value=mock_jira_instance)
        mock_jira_client.return_value.__aexit__ = AsyncMock(return_value=False)
        
        with patch('app.api.report.HtmlExporter') as mock_html_exporter:
            mock_exporter_instance = MagicMock()
            mock_exporter_instance.generate.return_value = "<html>Test Report</html>"
            mock_html_exporter.return_value = mock_exporter_instance
            
            response = client.post(
                "/reports/custom",
                json={"start_date": "2024-01-01", "end_date": "2024-01-31"}
            )
            
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")

    @patch('app.api.report.ReportBuilder')
    @patch('app.api.report.JiraClient')
    def test_custom_post_json_response(self, mock_jira_client, mock_report_builder, mock_settings, mock_report_data):
        """Test custom report POST with JSON format."""
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build_custom_report.return_value = mock_report_data
        mock_report_builder.return_value = mock_builder_instance
        
        mock_jira_instance = AsyncMock()
        mock_jira_client.return_value.__aenter__ = AsyncMock(return_value=mock_jira_instance)
        mock_jira_client.return_value.__aexit__ = AsyncMock(return_value=False)
        
        response = client.post(
            "/reports/custom?format=json",
            json={"start_date": "2024-01-01", "end_date": "2024-01-31"}
        )
        
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")


class TestAPIErrorHandling:
    """Tests for API error handling."""

    @patch('app.api.report.ReportBuilder')
    @patch('app.api.report.JiraClient')
    def test_report_generation_error(self, mock_jira_client, mock_report_builder):
        """Test handling of report generation errors."""
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build_report.side_effect = Exception("Test error")
        mock_report_builder.return_value = mock_builder_instance
        
        mock_jira_instance = AsyncMock()
        mock_jira_client.return_value.__aenter__ = AsyncMock(return_value=mock_jira_instance)
        mock_jira_client.return_value.__aexit__ = AsyncMock(return_value=False)
        
        response = client.get("/reports/monthly?year=2024&month=1")
        
        assert response.status_code == 500
        assert "Failed to generate report" in response.json().get("detail", "")


class TestAPIRequestParsing:
    """Tests for request parameter parsing."""

    def test_monthly_request_model(self):
        """Test MonthlyReportRequest model validation."""
        request = MonthlyReportRequest(year=2024, month=1)
        assert request.year == 2024
        assert request.month == 1
        assert request.group_by_projects is True
        assert request.include_raw_data is True

    def test_monthly_request_with_optional_fields(self):
        """Test MonthlyReportRequest with optional fields."""
        request = MonthlyReportRequest(
            year=2024,
            month=1,
            project_keys=["MB", "MAX"],
            group="IT"
        )
        assert request.project_keys == ["MB", "MAX"]
        assert request.group == "IT"

    def test_custom_request_model(self):
        """Test CustomReportRequest model validation."""
        request = CustomReportRequest(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        assert request.start_date == date(2024, 1, 1)
        assert request.end_date == date(2024, 1, 31)
        assert request.group_by_projects is True
        assert request.include_raw_data is True

    def test_custom_request_with_optional_fields(self):
        """Test CustomReportRequest with optional fields."""
        request = CustomReportRequest(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            project_keys=["MB"],
            group="IT"
        )
        assert request.project_keys == ["MB"]
        assert request.group == "IT"


class TestAPIResponseFormats:
    """Tests for different response formats."""

    @patch('app.api.report.ReportBuilder')
    @patch('app.api.report.JiraClient')
    def test_json_response_structure(self, mock_jira_client, mock_report_builder, mock_settings, mock_report_data):
        """Test JSON response has correct structure."""
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build_report.return_value = mock_report_data
        mock_report_builder.return_value = mock_builder_instance
        
        mock_jira_instance = AsyncMock()
        mock_jira_client.return_value.__aenter__ = AsyncMock(return_value=mock_jira_instance)
        mock_jira_client.return_value.__aexit__ = AsyncMock(return_value=False)
        
        response = client.get("/reports/monthly?year=2024&month=1&format=json")
        
        assert response.status_code == 200
        data = response.json()
        assert "year" in data
        assert "month" in data
        assert "total_worklog_hours" in data


class TestBuildShareableUrl:
    """Tests for _build_shareable_url function."""

    def test_build_monthly_shareable_url(self, mock_settings):
        """Test building shareable URL for monthly report."""
        from app.api.report import _build_shareable_url
        from app.models.schemas import MonthlyReportRequest
        
        request = MonthlyReportRequest(year=2024, month=1, project_keys=["MB"])
        report = MagicMock()
        report.year = 2024
        report.month = 1
        
        url = _build_shareable_url(request, report, is_monthly=True)
        
        assert "reports/monthly" in url
        assert "year=2024" in url
        assert "month=1" in url

    def test_build_custom_shareable_url(self, mock_settings):
        """Test building shareable URL for custom report."""
        from app.api.report import _build_shareable_url
        from app.models.schemas import CustomReportRequest
        
        request = CustomReportRequest(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        report = MagicMock()
        report.start_date = date(2024, 1, 1)
        
        url = _build_shareable_url(request, report, is_monthly=False)
        
        assert "reports/custom" in url
        assert "start_date=2024-01-01" in url
        assert "end_date=2024-01-31" in url
