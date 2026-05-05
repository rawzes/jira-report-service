"""
Builder Metrics module for Jira Report application.

This module contains methods for calculating flow metrics.
"""

import logging
from typing import List, Dict
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

from app.models.schemas import (
    ReportData, IssueData, WorklogEntry,
    WeeklyThroughput, CycleTimeData, AgingWipData,
    OverdueData, ReopenedData, StatusDistribution, WeeklyCycleTime
)

logger = logging.getLogger(__name__)


def calculate_flow_metrics(
    report: ReportData,
    issues: List[IssueData],
    done_statuses: List[str],
    start_statuses: List[str],
    blocked_statuses: List[str]
):
    """Calculate all flow metrics."""
    # Weekly throughput
    _calculate_weekly_throughput(report, issues, done_statuses)
    
    # Cycle time data
    _calculate_cycle_time_data(report, issues)
    
    # Aging WIP
    _calculate_aging_wip(report, issues, done_statuses)
    
    # Overdue tasks
    _calculate_overdue(report, issues, done_statuses)
    
    # Reopened tasks
    _calculate_reopened(report, issues, done_statuses)
    
    # WIP snapshot
    _calculate_wip_snapshot(report, issues, done_statuses, blocked_statuses)
    
    # Weekly cycle time
    _calculate_weekly_cycle_time(report, issues, done_statuses)
    
    # Status distribution
    _calculate_status_distribution(report, issues)
    
    # Raw transitions
    _collect_raw_transitions(report, issues)
    
    # Top oldest issues
    _calculate_top_oldest(report, issues, done_statuses)
    
    # Overall metrics
    report.throughput = sum(wt.closed_tasks_count for wt in report.weekly_throughput)
    
    # Median and P85 cycle time
    cycle_times = [ct.cycle_time_days for ct in report.cycle_time_data if ct.cycle_time_days is not None]
    if cycle_times:
        sorted_ct = sorted(cycle_times)
        report.median_cycle_time = statistics.median(sorted_ct)
        index_85 = int(len(sorted_ct) * 0.85)
        report.p85_cycle_time = sorted_ct[min(index_85, len(sorted_ct) - 1)]


def _calculate_weekly_throughput(
    report: ReportData,
    issues: List[IssueData],
    done_statuses: List[str]
):
    """Calculate weekly throughput."""
    week_ranges = _get_week_ranges(report.start_date, report.end_date)
    weekly_data = defaultdict(lambda: {"closed": 0, "created": 0})
    
    for week_start, week_end in week_ranges:
        for issue in issues:
            # Count created in week
            if issue.created and week_start <= issue.created < week_end:
                key = (week_start, week_end, issue.project_key)
                weekly_data[key]["created"] += 1
            
            # Count closed in week (using status_category_changed_date for done)
            if issue.status_category_changed_date and week_start <= issue.status_category_changed_date < week_end:
                if issue.status in done_statuses:
                    key = (week_start, week_end, issue.project_key)
                    weekly_data[key]["closed"] += 1
    
    for (week_start, week_end, project_key), counts in weekly_data.items():
        report.weekly_throughput.append(WeeklyThroughput(
            week_start=week_start,
            week_end=week_end,
            project_key=project_key,
            closed_tasks_count=counts["closed"],
            created_tasks_count=counts["created"],
            net_flow=counts["closed"] - counts["created"]
        ))


def _calculate_cycle_time_data(report: ReportData, issues: List[IssueData]):
    """Calculate cycle time for completed issues."""
    for issue in issues:
        if issue.cycle_time_days is not None:
            report.cycle_time_data.append(CycleTimeData(
                issue_key=issue.issue_key,
                project_key=issue.project_key,
                issue_type=issue.issue_type,
                assignee=issue.assignee_display_name,
                reporter=issue.reporter,
                start_progress_date=issue.start_progress_date,
                done_date=issue.resolution_date,
                cycle_time_days=issue.cycle_time_days,
                cycle_time_hours=issue.cycle_time_hours,
                reopened_flag=issue.reopened_flag
            ))


def _calculate_aging_wip(
    report: ReportData,
    issues: List[IssueData],
    done_statuses: List[str]
):
    """Calculate aging WIP for non-closed issues."""
    now = datetime.now().astimezone()
    
    for issue in issues:
        if issue.status not in done_statuses:
            aging_days = 0
            if issue.created:
                aging_days = (now - issue.created).days
            
            report.aging_wip_data.append(AgingWipData(
                issue_key=issue.issue_key,
                project_key=issue.project_key,
                status=issue.status,
                assignee=issue.assignee_display_name,
                created_date=issue.created,
                last_status_change_date=issue.last_status_change_date,
                aging_days=aging_days,
                blocked_flag=issue.blocked_flag,
                due_date=issue.due_date,
                overdue_flag=issue.overdue_flag
            ))
    
    report.aging_wip_count = len(report.aging_wip_data)


def _calculate_overdue(report: ReportData, issues: List[IssueData], done_statuses: List[str]):
    """Calculate overdue tasks."""
    now = datetime.now().astimezone()
    
    for issue in issues:
        if issue.due_date and issue.status not in done_statuses:
            if now > issue.due_date:
                days_overdue = (now - issue.due_date).days
                report.overdue_data.append(OverdueData(
                    issue_key=issue.issue_key,
                    project_key=issue.project_key,
                    assignee=issue.assignee_display_name,
                    status=issue.status,
                    due_date=issue.due_date,
                    days_overdue=days_overdue,
                    priority=issue.priority
                ))
    
    report.overdue_tasks_count = len(report.overdue_data)


def _calculate_reopened(
    report: ReportData,
    issues: List[IssueData],
    done_statuses: List[str]
):
    """Calculate reopened tasks."""
    for issue in issues:
        if issue.reopened_count > 0:
            # Find the last done date and first reopen date
            done_date = None
            reopen_date = None
            
            for trans in issue.transitions:
                if trans.to_status in done_statuses:
                    done_date = trans.transition_date
                if trans.from_status in done_statuses and trans.to_status not in done_statuses:
                    if reopen_date is None:
                        reopen_date = trans.transition_date
            
            report.reopened_data.append(ReopenedData(
                issue_key=issue.issue_key,
                project_key=issue.project_key,
                assignee=issue.assignee_display_name,
                done_date=done_date,
                reopen_date=reopen_date,
                reopen_count=issue.reopened_count,
                current_status=issue.status
            ))
    
    report.reopened_tasks_count = len(report.reopened_data)


def _calculate_wip_snapshot(
    report: ReportData,
    issues: List[IssueData],
    done_statuses: List[str],
    blocked_statuses: List[str]
):
    """Calculate WIP snapshot (non-closed issues)."""
    report.wip_count = sum(1 for issue in issues if issue.status not in done_statuses)
    
    # Also count blocked tasks
    report.blocked_tasks_count = sum(1 for issue in issues if issue.blocked_flag)


def _collect_raw_transitions(report: ReportData, issues: List[IssueData]):
    """Collect all raw transitions."""
    for issue in issues:
        report.raw_transitions.extend(issue.transitions)


def _calculate_top_oldest(report: ReportData, issues: List[IssueData], done_statuses: List[str]):
    """Calculate top 5 oldest non-closed issues."""
    now = datetime.now().astimezone()
    
    open_issues = [issue for issue in issues if issue.status not in done_statuses]
    open_issues.sort(key=lambda x: x.created or now, reverse=False)
    
    top_5 = open_issues[:5]
    report.top_oldest_issues = [
        {
            "issue_key": issue.issue_key,
            "project_key": issue.project_key,
            "summary": issue.summary,
            "status": issue.status,
            "created": issue.created.isoformat() if issue.created else None,
            "aging_days": (now - issue.created).days if issue.created else 0,
            "assignee": issue.assignee_display_name
        }
        for issue in top_5
    ]


def _calculate_weekly_cycle_time(
    report: ReportData,
    issues: List[IssueData],
    done_statuses: List[str]
):
    """Calculate weekly cycle time (median and P85)."""
    week_ranges = _get_week_ranges(report.start_date, report.end_date)
    weekly_cycle_data = defaultdict(list)
    
    for week_start, week_end in week_ranges:
        for issue in issues:
            if (issue.resolution_date and 
                week_start <= issue.resolution_date < week_end and 
                issue.cycle_time_days is not None):
                key = (week_start, week_end, issue.project_key)
                weekly_cycle_data[key].append(issue.cycle_time_days)
    
    for (week_start, week_end, project_key), cycle_times in weekly_cycle_data.items():
        if cycle_times:
            sorted_ct = sorted(cycle_times)
            median_ct = statistics.median(sorted_ct)
            index_85 = int(len(sorted_ct) * 0.85)
            p85_ct = sorted_ct[min(index_85, len(sorted_ct) - 1)]
            
            report.weekly_cycle_time.append(WeeklyCycleTime(
                week_start=week_start,
                week_end=week_end,
                project_key=project_key,
                median_cycle_time=median_ct,
                p85_cycle_time=p85_ct,
                tasks_count=len(cycle_times)
            ))


def _calculate_status_distribution(report: ReportData, issues: List[IssueData]):
    """Calculate status distribution by project."""
    status_data = defaultdict(lambda: defaultdict(int))
    
    for issue in issues:
        status_data[issue.project_key][issue.status] += 1
    
    for project_key, statuses in status_data.items():
        for status, count in statuses.items():
            report.status_distribution.append(StatusDistribution(
                project_key=project_key,
                status=status,
                count=count
            ))


def _get_week_ranges(
    start_date: datetime,
    end_date: datetime
) -> List[tuple]:
    """Get list of week ranges (Monday to Sunday) for the date range."""
    weeks = []
    current = start_date - timedelta(days=start_date.weekday())  # Go to Monday
    
    while current < end_date:
        week_start = current
        week_end = current + timedelta(days=7)
        if week_end > end_date:
            week_end = end_date
        weeks.append((week_start, week_end))
        current = week_end
    
    return weeks
