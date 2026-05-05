"""
Report Builder module for Jira Report application.

This module builds report data by aggregating metrics from Jira data.
Refactored from original 920 lines to use modular components.
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.models.schemas import (
    ReportData, MonthlyReportRequest, CustomReportRequest
)
from app.models.config import get_settings
from app.services.jira_client import JiraClient

from app.services.builder_data import (
    collect_all_issues_with_changelog,
    collect_worklogs,
)
from app.services.builder_metrics import calculate_flow_metrics
from app.services.builder_aggregators import (
    aggregate_employee_metrics,
    aggregate_project_metrics,
    filter_employees_by_group,
)

logger = logging.getLogger(__name__)


class ReportBuilder:
    """Builds report data by aggregating metrics from Jira data."""
    
    def __init__(self, jira_client: JiraClient):
        self.jira = jira_client
        self.settings = get_settings()
        self.timezone = ZoneInfo(self.settings.TIMEZONE)
        self.done_statuses = self.settings.done_statuses_list
        self.start_statuses = self.settings.start_statuses_list
        self.blocked_statuses = self.settings.blocked_statuses_list
        self.excluded_statuses = self.settings.excluded_statuses_list
    
    def _get_month_range(
        self, 
        year: int, 
        month: int
    ) -> tuple:
        """Get start and end datetime for a month."""
        start = datetime(year, month, 1, tzinfo=self.timezone)
        if month == 12:
            end = datetime(year + 1, 1, 1, tzinfo=self.timezone)
        else:
            end = datetime(year, month + 1, 1, tzinfo=self.timezone)
        return start, end
    
    def _get_effective_user_group(self, request) -> Optional[str]:
        """Get the effective user group from request or ENV settings."""
        if hasattr(request, 'group') and request.group:
            return request.group
        return self.settings.JIRA_USER_GROUP
    
    async def build_report(self, request) -> ReportData:
        """Build complete monthly report with flow metrics."""
        from app.models.schemas import MonthlyReportRequest
        
        if isinstance(request, dict):
            request = MonthlyReportRequest(**request)
        
        project_keys = request.project_keys or self.settings.project_keys_list
        start_date, end_date = self._get_month_range(request.year, request.month)
        
        # Get effective user group (from request or ENV)
        user_group = self._get_effective_user_group(request)
        
        report = ReportData(
            year=request.year,
            month=request.month,
            start_date=start_date,
            end_date=end_date,
            include_raw_data=getattr(request, 'include_raw_data', True)
        )
        
        # Collect all issues with changelog
        all_issues = await collect_all_issues_with_changelog(
            self.jira, project_keys, start_date, end_date,
            self.done_statuses, self.excluded_statuses
        )
        report.raw_issues = all_issues
        
        # Collect all worklogs
        all_worklogs = await collect_worklogs(
            self.jira, all_issues, start_date, end_date
        )
        report.raw_worklogs = all_worklogs
        
        # Calculate flow metrics
        calculate_flow_metrics(
            report, all_issues, 
            self.done_statuses, self.start_statuses, self.blocked_statuses
        )
        
        # Aggregate employee metrics
        report.employee_metrics = aggregate_employee_metrics(
            report, all_issues, all_worklogs, self.done_statuses
        )
        
        # Filter employees by Jira group if configured
        report.employee_metrics = await filter_employees_by_group(
            report.employee_metrics, self.jira, user_group
        )
        
        # Aggregate project metrics
        report.project_metrics = aggregate_project_metrics(
            report, report.employee_metrics,
            report.cycle_time_data, report.aging_wip_data,
            report.overdue_data, report.reopened_data,
            report.raw_issues, self.done_statuses, self.blocked_statuses
        )
        
        # Calculate totals
        report.total_worklog_hours = sum(em.worklog_hours for em in report.employee_metrics)
        report.total_created_issues = sum(em.created_issues for em in report.employee_metrics)
        report.total_closed_issues = sum(em.closed_issues for em in report.employee_metrics)
        
        return report
    
    async def build_custom_report(self, request) -> ReportData:
        """Build report for custom date range with flow metrics."""
        from app.models.schemas import CustomReportRequest
        from datetime import datetime as dt
        
        if isinstance(request, dict):
            request = CustomReportRequest(**request)
        
        project_keys = request.project_keys or self.settings.project_keys_list
        
        # Get effective user group (from request or ENV)
        user_group = self._get_effective_user_group(request)
        
        # Convert date to datetime with timezone
        # Use exclusive end_date (first moment of next day) for consistency with monthly reports
        start_date = dt.combine(request.start_date, dt.min.time()).replace(tzinfo=self.timezone)
        end_date = dt.combine(request.end_date + timedelta(days=1), dt.min.time()).replace(tzinfo=self.timezone)
        
        # Use year and month from start_date for ReportData
        report = ReportData(
            year=start_date.year,
            month=start_date.month,
            start_date=start_date,
            end_date=end_date,
            include_raw_data=getattr(request, 'include_raw_data', True)
        )
        
        # Collect all issues with changelog
        all_issues = await collect_all_issues_with_changelog(
            self.jira, project_keys, start_date, end_date,
            self.done_statuses, self.excluded_statuses
        )
        report.raw_issues = all_issues
        
        # Collect all worklogs
        all_worklogs = await collect_worklogs(
            self.jira, all_issues, start_date, end_date
        )
        report.raw_worklogs = all_worklogs
        
        # Calculate flow metrics
        calculate_flow_metrics(
            report, all_issues, 
            self.done_statuses, self.start_statuses, self.blocked_statuses
        )
        
        # Aggregate employee metrics
        report.employee_metrics = aggregate_employee_metrics(
            report, all_issues, all_worklogs, self.done_statuses
        )
        
        # Filter employees by Jira group if configured
        report.employee_metrics = await filter_employees_by_group(
            report.employee_metrics, self.jira, user_group
        )
        
        # Aggregate project metrics
        report.project_metrics = aggregate_project_metrics(
            report, report.employee_metrics,
            report.cycle_time_data, report.aging_wip_data,
            report.overdue_data, report.reopened_data,
            report.raw_issues, self.done_statuses, self.blocked_statuses
        )
        
        # Calculate totals
        report.total_worklog_hours = sum(em.worklog_hours for em in report.employee_metrics)
        report.total_created_issues = sum(em.created_issues for em in report.employee_metrics)
        report.total_closed_issues = sum(em.closed_issues for em in report.employee_metrics)
        
        return report
