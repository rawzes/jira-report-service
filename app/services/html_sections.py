"""
HTML Sections module for Jira Report application.

This module contains methods for generating different sections of the HTML report.
"""

from typing import List, Dict
from app.models.schemas import (
    ReportData, EmployeeMetrics, ProjectMetrics, 
    IssueData, WorklogEntry, IssueTransition,
    WeeklyThroughput, WeeklyCycleTime, CycleTimeData, AgingWipData,
    OverdueData, ReopenedData, StatusDistribution
)
from app.services.localization import get_localization


def generate_summary_section(report: ReportData, jira_base: str, _: Dict,
                              created_jql: str, closed_jql: str,
                              overdue_jql: str, reopened_jql: str, blocked_jql: str,
                              created_jql_encoded: str = None, closed_jql_encoded: str = None,
                              overdue_jql_encoded: str = None, reopened_jql_encoded: str = None,
                              blocked_jql_encoded: str = None) -> str:
    """Generate summary section with JIRA links and navigation."""
    html = f"<h2>{_['summary']}</h2>"
    
    # Use encoded JQL if provided, otherwise use raw JQL
    if created_jql_encoded is None:
        created_jql_encoded = created_jql
    if closed_jql_encoded is None:
        closed_jql_encoded = closed_jql
    if overdue_jql_encoded is None:
        overdue_jql_encoded = overdue_jql
    if reopened_jql_encoded is None:
        reopened_jql_encoded = reopened_jql
    if blocked_jql_encoded is None:
        blocked_jql_encoded = blocked_jql
    
    html += '<div class="metrics-grid">'
    
    metrics = [
        (_["total_worklog_hours"], f"{report.total_worklog_hours:.2f}"),
        (_["total_created_issues"], f'<a href="{jira_base}/issues/?jql={created_jql_encoded}" target="_blank">{report.total_created_issues}</a>'),
        (_["total_closed_issues"], f'<a href="{jira_base}/issues/?jql={closed_jql_encoded}" target="_blank">{report.total_closed_issues}</a>'),
        (_["throughput"], str(report.throughput)),
        (_["median_cycle_time"], f"{report.median_cycle_time:.2f}" if report.median_cycle_time else "N/A"),
        (_["p85_cycle_time"], f"{report.p85_cycle_time:.2f}" if report.p85_cycle_time else "N/A"),
        (_["overdue_tasks"], f'<a href="{jira_base}/issues/?jql={overdue_jql_encoded}" target="_blank">{report.overdue_tasks_count}</a>'),
        (_["reopened_tasks"], f'<a href="{jira_base}/issues/?jql={reopened_jql_encoded}" target="_blank">{report.reopened_tasks_count}</a>'),
        (_["blocked_tasks"], f'<a href="{jira_base}/issues/?jql={blocked_jql_encoded}" target="_blank">{report.blocked_tasks_count}</a>'),
    ]
    
    for label, value in metrics:
        html += f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """
    
    html += '</div>'
    
    # Top 5 oldest issues
    if report.top_oldest_issues:
        html += f"<h3>{_['top_oldest_issues']}</h3>"
        html += "<div class='table-responsive'><table><thead><tr>"
        for header in [_["issue_key"], _["summary"], _["project_key"], 
                      _["status"], _["aging_days"], _["assignee"]]:
            html += f"<th>{header}</th>"
        html += "</tr></thead><tbody>"
        
        for issue in report.top_oldest_issues:
            issue_key = issue.get('issue_key', '')
            html += "<tr>"
            html += f"<td><a href='{jira_base}/browse/{issue_key}' target='_blank'>{issue_key}</a></td>"
            html += f"<td>{issue.get('summary', '')}</td>"
            html += f"<td>{issue.get('project_key', '')}</td>"
            html += f"<td>{issue.get('status', '')}</td>"
            html += f"<td>{issue.get('aging_days', 0)}</td>"
            html += f"<td>{issue.get('assignee', '')}</td>"
            html += "</tr>"
        
        html += "</tbody></table></div>"
    
    return html


def generate_by_employee_section(report: ReportData, jira_base: str, _: Dict) -> str:
    """Generate by employee section - Account ID hidden."""
    if not report.employee_metrics:
        return ""
    
    html = f"<h2>{_['by_employee']}</h2>"
    html += "<div class='table-responsive'><table><thead><tr>"
    # Removed account_id from headers
    for header in [_["employee_name"], _["project_key"],
                  _["worklog_hours"], _["created_issues"], _["closed_issues"],
                  _["reopen_count"], _["active_wip"], _["avg_cycle_time"],
                  _["median_cycle_time"], _["overdue_count"]]:
        html += f"<th>{header}</th>"
    html += "</tr></thead><tbody>"
    
    for emp in report.employee_metrics:
        html += "<tr>"
        html += f"<td>{emp.display_name}</td>"
        # Account ID hidden
        html += f"<td><a href='{jira_base}/projects/{emp.project_key}' target='_blank'>{emp.project_key}</a></td>"
        html += f"<td>{emp.worklog_hours:.2f}</td>"
        html += f"<td>{emp.created_issues}</td>"
        html += f"<td>{emp.closed_issues}</td>"
        html += f"<td>{emp.reopened_tasks}</td>"
        html += f"<td>{emp.active_wip}</td>"
        html += f"<td>{f'{emp.avg_cycle_time:.2f}' if emp.avg_cycle_time is not None else 'N/A'}</td>"
        html += f"<td>{f'{emp.median_cycle_time:.2f}' if emp.median_cycle_time is not None else 'N/A'}</td>"
        html += f"<td>{emp.overdue_tasks}</td>"
        html += "</tr>"
    
    # Total row
    html += '<tr class="total-row">'
    html += f"<td>{_['total']}</td><td></td>"
    html += f"<td>{sum(e.worklog_hours for e in report.employee_metrics):.2f}</td>"
    html += f"<td>{sum(e.created_issues for e in report.employee_metrics)}</td>"
    html += f"<td>{sum(e.closed_issues for e in report.employee_metrics)}</td>"
    html += f"<td>{sum(e.reopened_tasks for e in report.employee_metrics)}</td>"
    html += f"<td>{sum(e.active_wip for e in report.employee_metrics)}</td>"
    html += f"<td></td><td></td>"
    html += f"<td>{sum(e.overdue_tasks for e in report.employee_metrics)}</td>"
    html += "</tr>"
    
    html += "</tbody></table></div>"
    return html


def generate_by_project_section(report: ReportData, jira_base: str, _: Dict) -> str:
    """Generate by project section with responsive wrapper."""
    if not report.project_metrics:
        return ""
    
    html = f"<h2>{_['by_project']}</h2>"
    html += "<div class='table-responsive'><table><thead><tr>"
    for header in [_["project_key"], _["worklog_hours"], _["created_issues"],
                  _["closed_issues"], _["throughput_count"], _["median_cycle_time"],
                  _["p85_cycle_time"], _["wip_count"], _["aging_7"],
                  _["aging_14"], _["aging_30"], _["reopen_count"],
                  _["overdue_count"], _["blocked_count"]]:
        html += f"<th>{header}</th>"
    html += "</tr></thead><tbody>"
    
    for proj in report.project_metrics:
        html += "<tr>"
        html += f"<td><a href='{jira_base}/projects/{proj.project_key}' target='_blank'>{proj.project_key}</a></td>"
        html += f"<td>{proj.worklog_hours:.2f}</td>"
        html += f"<td>{proj.created_issues}</td>"
        html += f"<td>{proj.closed_issues}</td>"
        html += f"<td>{proj.throughput}</td>"
        html += f"<td>{f'{proj.median_cycle_time:.2f}' if proj.median_cycle_time is not None else 'N/A'}</td>"
        html += f"<td>{f'{proj.p85_cycle_time:.2f}' if proj.p85_cycle_time is not None else 'N/A'}</td>"
        html += f"<td>{proj.wip_count}</td>"
        html += f"<td>{proj.aging_wip_7}</td>"
        html += f"<td>{proj.aging_wip_14}</td>"
        html += f"<td>{proj.aging_wip_30}</td>"
        html += f"<td>{proj.reopened_tasks}</td>"
        html += f"<td>{proj.overdue_tasks}</td>"
        html += f"<td>{proj.blocked_tasks}</td>"
        html += "</tr>"
    
    # Total row
    html += '<tr class="total-row">'
    html += f"<td>{_['total']}</td>"
    html += f"<td>{sum(p.worklog_hours for p in report.project_metrics):.2f}</td>"
    html += f"<td>{sum(p.created_issues for p in report.project_metrics)}</td>"
    html += f"<td>{sum(p.closed_issues for p in report.project_metrics)}</td>"
    html += f"<td>{sum(p.throughput for p in report.project_metrics)}</td>"
    html += f"<td></td><td></td>"
    html += f"<td>{sum(p.wip_count for p in report.project_metrics)}</td>"
    html += f"<td></td><td></td><td></td>"
    html += f"<td>{sum(p.reopened_tasks for p in report.project_metrics)}</td>"
    html += f"<td>{sum(p.overdue_tasks for p in report.project_metrics)}</td>"
    html += f"<td>{sum(p.blocked_tasks for p in report.project_metrics)}</td>"
    html += "</tr>"
    
    html += "</tbody></table></div>"
    return html


def generate_weekly_throughput_section(report: ReportData, jira_base: str, _: Dict) -> str:
    """Generate weekly throughput section with responsive wrapper."""
    if not report.weekly_throughput:
        return ""
    
    html = f"<h2>{_['weekly_throughput']}</h2>"
    html += "<div class='table-responsive'><table><thead><tr>"
    for header in [_["week_start"], _["week_end"], _["project_key"],
                  _["closed_count"], _["created_count"], _["net_flow"]]:
        html += f"<th>{header}</th>"
    html += "</tr></thead><tbody>"
    
    for wt in report.weekly_throughput:
        html += "<tr>"
        html += f"<td>{wt.week_start.strftime('%Y-%m-%d')}</td>"
        html += f"<td>{wt.week_end.strftime('%Y-%m-%d')}</td>"
        html += f"<td><a href='{jira_base}/projects/{wt.project_key}' target='_blank'>{wt.project_key}</a></td>"
        html += f"<td>{wt.closed_tasks_count}</td>"
        html += f"<td>{wt.created_tasks_count}</td>"
        html += f"<td>{wt.net_flow}</td>"
        html += "</tr>"
    
    html += "</tbody></table></div>"
    return html


def generate_cycle_time_section(report: ReportData, jira_base: str, _: Dict) -> str:
    """Generate cycle time section with clickable issue keys."""
    if not report.cycle_time_data:
        return ""
    
    html = f"<h2>{_['cycle_time']}</h2>"
    html += "<div class='table-responsive'><table><thead><tr>"
    for header in [_["issue_key"], _["project_key"], _["issue_type"],
                  _["assignee"], _["reporter"], _["start_progress_date"],
                  _["done_date"], _["cycle_time_days"], _["cycle_time_hours"],
                  _["reopened_flag"]]:
        html += f"<th>{header}</th>"
    html += "</tr></thead><tbody>"
    
    for ct in report.cycle_time_data:
        html += "<tr>"
        html += f"<td><a href='{jira_base}/browse/{ct.issue_key}' target='_blank'>{ct.issue_key}</a></td>"
        html += f"<td><a href='{jira_base}/projects/{ct.project_key}' target='_blank'>{ct.project_key}</a></td>"
        html += f"<td>{ct.issue_type or ''}</td>"
        html += f"<td>{ct.assignee or ''}</td>"
        html += f"<td>{ct.reporter or ''}</td>"
        html += f"<td>{ct.start_progress_date.strftime('%Y-%m-%d') if ct.start_progress_date else ''}</td>"
        html += f"<td>{ct.done_date.strftime('%Y-%m-%d') if ct.done_date else ''}</td>"
        html += f"<td>{f'{ct.cycle_time_days:.2f}' if ct.cycle_time_days is not None else 'N/A'}</td>"
        html += f"<td>{f'{ct.cycle_time_hours:.2f}' if ct.cycle_time_hours is not None else 'N/A'}</td>"
        html += f"<td>{'Yes' if ct.reopened_flag else 'No'}</td>"
        html += "</tr>"
    
    html += "</tbody></table></div>"
    return html


def generate_aging_wip_section(report: ReportData, jira_base: str, _: Dict) -> str:
    """Generate aging WIP section with clickable issue keys."""
    if not report.aging_wip_data:
        return ""
    
    html = f"<h2>{_['aging_wip']}</h2>"
    html += "<div class='table-responsive'><table><thead><tr>"
    for header in [_["issue_key"], _["project_key"], _["status"],
                  _["assignee"], _["created"], _["last_status_change"],
                  _["aging_days"], _["blocked_flag"], _["due_date"],
                  _["overdue_flag"]]:
        html += f"<th>{header}</th>"
    html += "</tr></thead><tbody>"
    
    for aw in report.aging_wip_data:
        html += "<tr>"
        html += f"<td><a href='{jira_base}/browse/{aw.issue_key}' target='_blank'>{aw.issue_key}</a></td>"
        html += f"<td><a href='{jira_base}/projects/{aw.project_key}' target='_blank'>{aw.project_key}</a></td>"
        html += f"<td>{aw.status}</td>"
        html += f"<td>{aw.assignee or ''}</td>"
        html += f"<td>{aw.created_date.strftime('%Y-%m-%d') if aw.created_date else ''}</td>"
        html += f"<td>{aw.last_status_change_date.strftime('%Y-%m-%d') if aw.last_status_change_date else ''}</td>"
        html += f"<td>{aw.aging_days}</td>"
        html += f"<td>{'Yes' if aw.blocked_flag else 'No'}</td>"
        html += f"<td>{aw.due_date.strftime('%Y-%m-%d') if aw.due_date else ''}</td>"
        html += f"<td>{'Yes' if aw.overdue_flag else 'No'}</td>"
        html += "</tr>"
    
    html += "</tbody></table></div>"
    return html


def generate_overdue_section(report: ReportData, jira_base: str, _: Dict) -> str:
    """Generate overdue section with clickable issue keys."""
    if not report.overdue_data:
        return ""
    
    html = f"<h2>{_['overdue']}</h2>"
    html += "<div class='table-responsive'><table><thead><tr>"
    for header in [_["issue_key"], _["project_key"], _["assignee"],
                  _["status"], _["due_date"], _["days_overdue"],
                  _["priority"]]:
        html += f"<th>{header}</th>"
    html += "</tr></thead><tbody>"
    
    for od in report.overdue_data:
        html += "<tr>"
        html += f"<td><a href='{jira_base}/browse/{od.issue_key}' target='_blank'>{od.issue_key}</a></td>"
        html += f"<td><a href='{jira_base}/projects/{od.project_key}' target='_blank'>{od.project_key}</a></td>"
        html += f"<td>{od.assignee or ''}</td>"
        html += f"<td>{od.status}</td>"
        html += f"<td>{od.due_date.strftime('%Y-%m-%d') if od.due_date else ''}</td>"
        html += f"<td>{od.days_overdue}</td>"
        html += f"<td>{od.priority or ''}</td>"
        html += "</tr>"
    
    html += "</tbody></table></div>"
    return html


def generate_reopened_section(report: ReportData, jira_base: str, _: Dict) -> str:
    """Generate reopened section with clickable issue keys."""
    if not report.reopened_data:
        return ""
    
    html = f"<h2>{_['reopened']}</h2>"
    html += "<div class='table-responsive'><table><thead><tr>"
    for header in [_["issue_key"], _["project_key"], _["assignee"],
                  _["done_date"], _["reopen_date"], _["reopen_count"],
                  _["current_status"]]:
        html += f"<th>{header}</th>"
    html += "</tr></thead><tbody>"
    
    for rd in report.reopened_data:
        html += "<tr>"
        html += f"<td><a href='{jira_base}/browse/{rd.issue_key}' target='_blank'>{rd.issue_key}</a></td>"
        html += f"<td><a href='{jira_base}/projects/{rd.project_key}' target='_blank'>{rd.project_key}</a></td>"
        html += f"<td>{rd.assignee or ''}</td>"
        html += f"<td>{rd.done_date.strftime('%Y-%m-%d') if rd.done_date else ''}</td>"
        html += f"<td>{rd.reopen_date.strftime('%Y-%m-%d') if rd.reopen_date else ''}</td>"
        html += f"<td>{rd.reopen_count}</td>"
        html += f"<td>{rd.current_status}</td>"
        html += "</tr>"
    
    html += "</tbody></table></div>"
    return html


def generate_employee_worklog_summary_section(report: ReportData, _: Dict) -> str:
    """Generate employee worklog hours summary - total hours per employee across all projects."""
    if not report.employee_metrics:
        return ""
    
    # Aggregate worklog hours by employee (across all projects)
    employee_totals = {}
    for emp in report.employee_metrics:
        key = emp.display_name  # Use display_name as key
        if key not in employee_totals:
            employee_totals[key] = {
                'display_name': emp.display_name,
                'total_hours': 0.0,
                'projects': set()
            }
        employee_totals[key]['total_hours'] += emp.worklog_hours
        employee_totals[key]['projects'].add(emp.project_key)
    
    # Sort by total hours descending
    sorted_employees = sorted(employee_totals.values(), key=lambda x: x['total_hours'], reverse=True)
    
    html = f"<h2>{_get(_, 'worklog_by_employee', 'Worklog by Employee')}</h2>"
    html += "<div class='table-responsive'><table><thead><tr>"
    for header in [_get(_, 'employee_name', 'Employee Name'), 
                  _get(_, 'worklog_hours', 'Worklog Hours'),
                  _get(_, 'project_key', 'Projects Count')]:
        html += f"<th>{header}</th>"
    html += "</tr></thead><tbody>"
    
    for emp in sorted_employees:
        html += "<tr>"
        html += f"<td>{emp['display_name']}</td>"
        html += f"<td>{emp['total_hours']:.2f}</td>"
        html += f"<td>{len(emp['projects'])}</td>"
        html += "</tr>"
    
    # Total row
    html += '<tr class="total-row">'
    html += f"<td>{_get(_, 'total', 'TOTAL')}</td>"
    html += f"<td>{sum(e['total_hours'] for e in sorted_employees):.2f}</td>"
    html += f"<td>{len(employee_totals)}</td>"
    html += "</tr>"
    
    html += "</tbody></table></div>"
    return html


def generate_raw_data_sections(report: ReportData, jira_base: str, _: Dict) -> str:
    """Generate raw data sections with responsive wrappers and clickable issue keys."""
    html = ""
    
    # Raw Issues
    if report.raw_issues:
        html += f"<h2>{_['raw_issues']}</h2>"
        html += "<div class='table-responsive'><table><thead><tr>"
        for header in [_["issue_key"], _["project_key"], _["issue_type"],
                      _["summary"], _["status"], _["created"],
                      _["assignee"], _["reporter"], _["due_date"],
                      _["priority"], _["cycle_time_days"], _["reopened_flag"],
                      _["blocked_flag"], _["overdue_flag"], _["aging_days"]]:
            html += f"<th>{header}</th>"
        html += "</tr></thead><tbody>"
        
        for issue in report.raw_issues:
            html += "<tr>"
            html += f"<td><a href='{jira_base}/browse/{issue.issue_key}' target='_blank'>{issue.issue_key}</a></td>"
            html += f"<td><a href='{jira_base}/projects/{issue.project_key}' target='_blank'>{issue.project_key}</a></td>"
            html += f"<td>{issue.issue_type or ''}</td>"
            html += f"<td>{issue.summary}</td>"
            html += f"<td>{issue.status}</td>"
            html += f"<td>{issue.created.strftime('%Y-%m-%d') if issue.created else ''}</td>"
            html += f"<td>{issue.assignee_display_name or ''}</td>"
            html += f"<td>{issue.reporter or ''}</td>"
            html += f"<td>{issue.due_date.strftime('%Y-%m-%d') if issue.due_date else ''}</td>"
            html += f"<td>{issue.priority or ''}</td>"
            html += f"<td>{f'{issue.cycle_time_days:.2f}' if issue.cycle_time_days is not None else 'N/A'}</td>"
            html += f"<td>{'Yes' if issue.reopened_flag else 'No'}</td>"
            html += f"<td>{'Yes' if issue.blocked_flag else 'No'}</td>"
            html += f"<td>{'Yes' if issue.overdue_flag else 'No'}</td>"
            html += f"<td>{issue.aging_days if issue.aging_days else 'N/A'}</td>"
            html += "</tr>"
        
        html += "</tbody></table></div>"
    
    # Raw Worklogs
    if report.raw_worklogs:
        html += f"<h2>{_['raw_worklogs']}</h2>"
        html += "<div class='table-responsive'><table><thead><tr>"
        for header in [_["issue_key"], _["project_key"], _["employee_name"],
                      _["started"], _["time_spent_hours"], _["comment"]]:
            html += f"<th>{header}</th>"
        html += "</tr></thead><tbody>"
        
        for wl in report.raw_worklogs:
            html += "<tr>"
            html += f"<td><a href='{jira_base}/browse/{wl.issue_key}' target='_blank'>{wl.issue_key}</a></td>"
            html += f"<td><a href='{jira_base}/projects/{wl.project_key}' target='_blank'>{wl.project_key}</a></td>"
            html += f"<td>{wl.display_name}</td>"
            html += f"<td>{wl.started.strftime('%Y-%m-%d %H:%M') if wl.started else ''}</td>"
            html += f"<td>{wl.time_spent_hours:.2f}</td>"
            html += f"<td>{wl.comment or ''}</td>"
            html += "</tr>"
        
        html += "</tbody></table></div>"
    
    # Raw Transitions
    if report.raw_transitions:
        html += f"<h2>{_['raw_transitions']}</h2>"
        html += "<div class='table-responsive'><table><thead><tr>"
        for header in [_["issue_key"], _["project_key"], _["from_status"],
                      _["to_status"], _["transition_date"], _["transition_author"]]:
            html += f"<th>{header}</th>"
        html += "</tr></thead><tbody>"
        
        for trans in report.raw_transitions:
            html += "<tr>"
            html += f"<td><a href='{jira_base}/browse/{trans.issue_key}' target='_blank'>{trans.issue_key}</a></td>"
            html += f"<td><a href='{jira_base}/projects/{trans.project_key}' target='_blank'>{trans.project_key}</a></td>"
            html += f"<td>{trans.from_status}</td>"
            html += f"<td>{trans.to_status}</td>"
            html += f"<td>{trans.transition_date.strftime('%Y-%m-%d %H:%M') if trans.transition_date else ''}</td>"
            html += f"<td>{trans.transition_author or ''}</td>"
            html += "</tr>"
        
        html += "</tbody></table></div>"
    
    return html


def _get(_: Dict, key: str, default=None):
    """Safe get from localization dict."""
    return _.get(key, default) if _ else default
