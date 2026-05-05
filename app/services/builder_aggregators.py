"""
Builder Aggregators module for Jira Report application.

This module contains methods for aggregating metrics by employee and project.
"""

import logging
from typing import List, Dict, Tuple, Set
from collections import defaultdict
import statistics

from app.models.schemas import (
    ReportData, IssueData, WorklogEntry, 
    EmployeeMetrics, ProjectMetrics
)
from app.services.jira_client import JiraClient

logger = logging.getLogger(__name__)


def aggregate_employee_metrics(
    report: ReportData,
    issues: List[IssueData],
    worklogs: List[WorklogEntry],
    done_statuses: List[str]
) -> List[EmployeeMetrics]:
    """Aggregate metrics per employee per project."""
    emp_metrics: Dict[Tuple[str, str], EmployeeMetrics] = {}
    
    # Aggregate worklogs
    for wl in worklogs:
        emp_key = _get_employee_key(wl.account_id, wl.display_name)
        key = (emp_key, wl.project_key)
        
        if key not in emp_metrics:
            emp_metrics[key] = EmployeeMetrics(
                account_id=wl.account_id,
                display_name=wl.display_name,
                project_key=wl.project_key
            )
        emp_metrics[key].worklog_hours += wl.time_spent_hours
    
    # Aggregate created issues
    for issue in issues:
        if not issue.created or not (report.start_date <= issue.created < report.end_date):
            continue
        if not issue.creator_account_id:
            continue
        
        emp_key = _get_employee_key(issue.creator_account_id, issue.creator_display_name)
        key = (emp_key, issue.project_key)
        
        if key not in emp_metrics:
            emp_metrics[key] = EmployeeMetrics(
                account_id=issue.creator_account_id,
                display_name=issue.creator_display_name,
                project_key=issue.project_key
            )
        emp_metrics[key].created_issues += 1
    
    # Aggregate closed issues
    for issue in issues:
        if not issue.status_category_changed_date:
            continue
        if not (report.start_date <= issue.status_category_changed_date < report.end_date):
            continue
        if issue.status not in done_statuses:
            continue
        if not issue.assignee_account_id:
            continue
        
        emp_key = _get_employee_key(issue.assignee_account_id, issue.assignee_display_name)
        key = (emp_key, issue.project_key)
        
        if key not in emp_metrics:
            emp_metrics[key] = EmployeeMetrics(
                account_id=issue.assignee_account_id,
                display_name=issue.assignee_display_name,
                project_key=issue.project_key
            )
        emp_metrics[key].closed_issues += 1
    
    # Aggregate reopened tasks
    for issue in issues:
        if issue.reopened_count > 0 and issue.assignee_account_id:
            emp_key = _get_employee_key(issue.assignee_account_id, issue.assignee_display_name)
            key = (emp_key, issue.project_key)
            
            if key in emp_metrics:
                emp_metrics[key].reopened_tasks += 1
    
    # Calculate active WIP per employee
    for issue in issues:
        if issue.status not in done_statuses and issue.assignee_account_id:
            emp_key = _get_employee_key(issue.assignee_account_id, issue.assignee_display_name)
            # Find which project this issue belongs to
            for key in emp_metrics:
                if key[0] == emp_key and key[1] == issue.project_key:
                    emp_metrics[key].active_wip += 1
                    break
    
    # Calculate overdue per employee
    for issue in issues:
        if issue.overdue_flag and issue.assignee_account_id:
            emp_key = _get_employee_key(issue.assignee_account_id, issue.assignee_display_name)
            for key in emp_metrics:
                if key[0] == emp_key and key[1] == issue.project_key:
                    emp_metrics[key].overdue_tasks += 1
                    break
    
    # Calculate cycle time per employee
    employee_cycle_times = defaultdict(list)
    for issue in issues:
        if issue.cycle_time_days is not None and issue.assignee_account_id:
            emp_key = _get_employee_key(issue.assignee_account_id, issue.assignee_display_name)
            employee_cycle_times[emp_key].append(issue.cycle_time_days)
    
    for key, cycle_times in employee_cycle_times.items():
        if key in emp_metrics:
            emp_metrics[key].avg_cycle_time = sum(cycle_times) / len(cycle_times)
            emp_metrics[key].median_cycle_time = statistics.median(sorted(cycle_times))
    
    return list(emp_metrics.values())


def aggregate_project_metrics(
    report: ReportData,
    employee_metrics: List[EmployeeMetrics],
    cycle_time_data: List,
    aging_wip_data: List,
    overdue_data: List,
    reopened_data: List,
    raw_issues: List[IssueData],
    done_statuses: List[str],
    blocked_statuses: List[str]
) -> List[ProjectMetrics]:
    """Aggregate metrics per project."""
    project_data: Dict[str, ProjectMetrics] = {}
    project_employees: Dict[str, set] = defaultdict(set)
    
    for emp in employee_metrics:
        if emp.project_key not in project_data:
            project_data[emp.project_key] = ProjectMetrics(
                project_key=emp.project_key
            )
        
        project_data[emp.project_key].worklog_hours += emp.worklog_hours
        project_data[emp.project_key].created_issues += emp.created_issues
        project_data[emp.project_key].closed_issues += emp.closed_issues
        project_employees[emp.project_key].add(emp.account_id)
    
    # Calculate additional project metrics
    for proj_key, metrics in project_data.items():
        metrics.employee_count = len(project_employees[proj_key])
        metrics.throughput = metrics.closed_issues
        
        # Cycle time for project
        project_cycle_times = [
            ct.cycle_time_days for ct in cycle_time_data 
            if ct.project_key == proj_key and ct.cycle_time_days is not None
        ]
        if project_cycle_times:
            sorted_ct = sorted(project_cycle_times)
            metrics.median_cycle_time = statistics.median(sorted_ct)
            index_85 = int(len(sorted_ct) * 0.85)
            metrics.p85_cycle_time = sorted_ct[min(index_85, len(sorted_ct) - 1)]
        
        # WIP count for project
        metrics.wip_count = sum(
            1 for aw in aging_wip_data if aw.project_key == proj_key
        )
        
        # Aging WIP buckets
        for aw in aging_wip_data:
            if aw.project_key == proj_key:
                if aw.aging_days > 7:
                    metrics.aging_wip_7 += 1
                if aw.aging_days > 14:
                    metrics.aging_wip_14 += 1
                if aw.aging_days > 30:
                    metrics.aging_wip_30 += 1
        
        # Reopened tasks
        metrics.reopened_tasks = sum(
            1 for rd in reopened_data if rd.project_key == proj_key
        )
        
        # Overdue tasks
        metrics.overdue_tasks = sum(
            1 for od in overdue_data if od.project_key == proj_key
        )
        
        # Blocked tasks
        metrics.blocked_tasks = sum(
            1 for issue in raw_issues 
            if issue.project_key == proj_key and issue.blocked_flag
        )
    
    return list(project_data.values())


async def filter_employees_by_group(
    employee_metrics: List[EmployeeMetrics],
    jira_client: JiraClient,
    user_group: str
) -> List[EmployeeMetrics]:
    """Filter employee metrics to only include users from the configured Jira group."""
    if not user_group:
        return employee_metrics
    
    try:
        logger.info(f"Fetching members of Jira group: {user_group}")
        group_members = await jira_client.get_group_members(user_group)
        
        # Extract account IDs from group members
        group_account_ids = {member.get("accountId") for member in group_members if member.get("accountId")}
        
        if not group_account_ids:
            logger.warning(f"No members found in group {user_group}")
            return employee_metrics
        
        # Filter employee metrics to only include users in the group
        original_count = len(employee_metrics)
        filtered_metrics = [
            emp for emp in employee_metrics
            if emp.account_id in group_account_ids
        ]
        
        filtered_count = original_count - len(filtered_metrics)
        if filtered_count > 0:
            logger.info(f"Filtered out {filtered_count} employees not in group '{user_group}'")
        
        logger.info(f"Report now includes {len(filtered_metrics)} employees from group '{user_group}'")
        return filtered_metrics
        
    except Exception as e:
        logger.error(f"Failed to filter employees by group '{user_group}': {e}")
        # Continue without filtering if there's an error
        return employee_metrics


def _get_employee_key(account_id: str, display_name: str) -> str:
    """Get unique employee key."""
    return f"{account_id}::{display_name}"
