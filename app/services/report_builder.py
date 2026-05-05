import asyncio
import logging
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
import statistics

from app.models.schemas import (
    ReportData, IssueData, WorklogEntry, EmployeeMetrics, ProjectMetrics, 
    IssueTransition, WeeklyThroughput, CycleTimeData, AgingWipData,
    OverdueData, ReopenedData, StatusDistribution
)
from app.models.config import settings

logger = logging.getLogger(__name__)


def _extract_text_from_adf(adf_doc: Optional[Dict]) -> str:
    """Extract plain text from Atlassian Document Format (ADF) comment."""
    if not adf_doc or not isinstance(adf_doc, dict):
        return ""
    
    text_parts = []
    
    def _traverse(node):
        if isinstance(node, dict):
            if node.get("type") == "text":
                text_parts.append(node.get("text", ""))
            if "content" in node and isinstance(node["content"], list):
                for child in node["content"]:
                    _traverse(child)
        elif isinstance(node, list):
            for item in node:
                _traverse(item)
    
    _traverse(adf_doc)
    return " ".join(text_parts).strip()


class ReportBuilder:
    """Builds report data by aggregating metrics from Jira data."""
    
    def __init__(self, jira_client):
        self.jira = jira_client
        self.timezone = ZoneInfo(settings.TIMEZONE)
        self.done_statuses = settings.done_statuses_list
        self.start_statuses = settings.start_statuses_list
        self.blocked_statuses = settings.blocked_statuses_list
        self.excluded_statuses = settings.excluded_statuses_list
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse Jira datetime string to datetime with timezone."""
        if not date_str:
            return None
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.astimezone(self.timezone)
        except Exception as e:
            logger.warning(f"Failed to parse datetime '{date_str}': {e}")
            return None
    
    def _get_month_range(
        self, 
        year: int, 
        month: int
    ) -> Tuple[datetime, datetime]:
        """Get start and end datetime for a month."""
        start = datetime(year, month, 1, tzinfo=self.timezone)
        if month == 12:
            end = datetime(year + 1, 1, 1, tzinfo=self.timezone)
        else:
            end = datetime(year, month + 1, 1, tzinfo=self.timezone)
        return start, end
    
    def _get_week_ranges(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Tuple[datetime, datetime]]:
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
    
    def _get_employee_key(self, account_id: str, display_name: str) -> str:
        """Get unique employee key."""
        return f"{account_id}::{display_name}"
    
    def _get_display_name(self, user_obj: Optional[Dict]) -> Tuple[Optional[str], Optional[str]]:
        """Extract account_id and display_name from Jira user object."""
        if not user_obj:
            return None, None
        
        if user_obj.get("accountId") is None and user_obj.get("displayName"):
            return "deleted", user_obj.get("displayName", "Deleted User")
        
        return user_obj.get("accountId"), user_obj.get("displayName")
    
    def _parse_issue_from_changelog(self, issue_data: Dict) -> IssueData:
        """Parse issue data including changelog to extract flow metrics."""
        fields = issue_data.get("fields", {})
        changelog = issue_data.get("changelog", {})
        histories = changelog.get("histories", [])
        
        project = fields.get("project", {})
        project_key = project.get("key", "UNKNOWN")
        
        creator_account_id, creator_display_name = self._get_display_name(fields.get("creator"))
        assignee_account_id, assignee_display_name = self._get_display_name(fields.get("assignee"))
        
        created = self._parse_datetime(fields.get("created"))
        resolution_date = self._parse_datetime(fields.get("resolutiondate"))
        
        issue_key = issue_data.get("key", "")
        issue_id = issue_data.get("id", "")
        issue_type = fields.get("issuetype", {}).get("name", "")
        summary = fields.get("summary", "")
        status = fields.get("status", {}).get("name", "")
        reporter = fields.get("reporter", {}).get("displayName") if fields.get("reporter") else None
        due_date = self._parse_datetime(fields.get("duedate"))
        priority = fields.get("priority", {}).get("name") if fields.get("priority") else None
        
        # Parse transitions from changelog
        transitions = []
        start_progress_date = None
        done_date = None
        reopened_count = 0
        was_done = False
        last_status_change_date = None
        
        # Sort histories by created date
        sorted_histories = sorted(histories, key=lambda h: h.get("created", ""))
        
        for history in sorted_histories:
            history_date = self._parse_datetime(history.get("created"))
            if not history_date:
                continue
            
            for item in history.get("items", []):
                if item.get("field") == "status":
                    from_status = item.get("fromString", "")
                    to_status = item.get("toString", "")
                    
                    # Record transition
                    transition = IssueTransition(
                        issue_key=issue_key,
                        project_key=project_key,
                        from_status=from_status,
                        to_status=to_status,
                        transition_date=history_date,
                        transition_author=history.get("author", {}).get("displayName")
                    )
                    transitions.append(transition)
                    
                    # Check for start progress
                    if to_status in self.start_statuses and start_progress_date is None:
                        start_progress_date = history_date
                    
                    # Check for done status
                    if to_status in self.done_statuses:
                        done_date = history_date
                        was_done = True
                    
                    # Check for reopen (from done to non-done)
                    if from_status in self.done_statuses and to_status not in self.done_statuses:
                        reopened_count += 1
                        was_done = False
                    
                    last_status_change_date = history_date
        
        # Calculate cycle time
        cycle_time_days = None
        cycle_time_hours = None
        if start_progress_date and done_date:
            delta = done_date - start_progress_date
            cycle_time_days = delta.total_seconds() / 86400.0
            cycle_time_hours = delta.total_seconds() / 3600.0
        
        # Check if blocked
        blocked_flag = status in self.blocked_statuses
        
        # Check if overdue
        overdue_flag = False
        if due_date and not done_date:
            overdue_flag = datetime.now(self.timezone) > due_date
        
        # Calculate aging days
        aging_days = None
        if not done_date and created:
            aging_days = (datetime.now(self.timezone) - created).days
        
        return IssueData(
            issue_key=issue_key,
            issue_id=issue_id,
            project_key=project_key,
            issue_type=issue_type,
            summary=summary,
            status=status,
            created=created,
            creator_account_id=creator_account_id,
            creator_display_name=creator_display_name,
            assignee_account_id=assignee_account_id,
            assignee_display_name=assignee_display_name,
            reporter=reporter,
            resolution_date=resolution_date,
            status_category_changed_date=done_date,
            start_progress_date=start_progress_date,
            cycle_time_days=cycle_time_days,
            cycle_time_hours=cycle_time_hours,
            reopened_count=reopened_count,
            reopened_flag=reopened_count > 0,
            blocked_flag=blocked_flag,
            overdue_flag=overdue_flag,
            due_date=due_date,
            priority=priority,
            aging_days=aging_days,
            transitions=transitions,
            last_status_change_date=last_status_change_date
        )
    
    def _get_effective_user_group(self, request) -> Optional[str]:
        """Get the effective user group from request or ENV settings."""
        if hasattr(request, 'group') and request.group:
            return request.group
        return settings.JIRA_USER_GROUP
    
    async def build_report(self, request) -> ReportData:
        """Build complete monthly report with flow metrics."""
        from app.models.schemas import MonthlyReportRequest
        
        if isinstance(request, dict):
            request = MonthlyReportRequest(**request)
        
        project_keys = request.project_keys or settings.project_keys_list
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
        all_issues = await self._collect_all_issues_with_changelog(project_keys, start_date, end_date)
        report.raw_issues = all_issues
        
        # Collect all worklogs
        all_worklogs = await self._collect_worklogs(all_issues, start_date, end_date)
        report.raw_worklogs = all_worklogs
        
        # Calculate flow metrics
        self._calculate_flow_metrics(report, all_issues)
        
        # Aggregate employee metrics
        self._aggregate_employee_metrics(report, all_issues, all_worklogs)
        
        # Filter employees by Jira group if configured
        await self._filter_employees_by_group(report, user_group)
        
        # Aggregate project metrics
        self._aggregate_project_metrics(report)
        
        # Calculate totals
        report.total_worklog_hours = sum(em.worklog_hours for em in report.employee_metrics)
        report.total_created_issues = sum(em.created_issues for em in report.employee_metrics)
        report.total_closed_issues = sum(em.closed_issues for em in report.employee_metrics)
        
        return report
    
    def _filter_excluded_statuses(self, issues: List[IssueData]) -> List[IssueData]:
        """Filter out issues with excluded statuses."""
        if not self.excluded_statuses:
            return issues
        
        filtered_issues = [issue for issue in issues if issue.status not in self.excluded_statuses]
        excluded_count = len(issues) - len(filtered_issues)
        if excluded_count > 0:
            logger.info(f"Filtered out {excluded_count} issues with excluded statuses: {self.excluded_statuses}")
        return filtered_issues

    async def _collect_all_issues_with_changelog(
        self,
        project_keys: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> List[IssueData]:
        """Collect all issues with their changelog history."""
        issues_dict = {}
        
        # Get all issues (created in period or updated in period)
        all_issues_jql = self.jira.build_all_issues_jql(project_keys, start_date, end_date)
        logger.info(f"Fetching all issues with JQL: {all_issues_jql}")
        
        issue_keys = []
        async for issues_page in self.jira.search_issues_jql(
            all_issues_jql,
            fields=["key"]
        ):
            for issue in issues_page:
                issue_keys.append(issue["key"])
        
        logger.info(f"Found {len(issue_keys)} issues to fetch with changelog")
        
        # Fetch each issue with changelog concurrently
        tasks = []
        for issue_key in issue_keys:
            tasks.append(self._fetch_issue_with_changelog(issue_key))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error fetching issue with changelog: {result}")
            elif result:
                issues_dict[result.issue_key] = result
        
        issues = list(issues_dict.values())
        return self._filter_excluded_statuses(issues)
    
    async def _fetch_issue_with_changelog(self, issue_key: str) -> Optional[IssueData]:
        """Fetch a single issue with its complete changelog."""
        try:
            issue_data = await self.jira.get_issue_changelog(issue_key)
            return self._parse_issue_from_changelog(issue_data)
        except Exception as e:
            logger.error(f"Failed to fetch issue {issue_key} with changelog: {e}")
            return None
    
    async def _collect_worklogs(
        self,
        issues: List[IssueData],
        start_date: datetime,
        end_date: datetime
    ) -> List[WorklogEntry]:
        """Collect all worklog entries for issues within date range."""
        all_worklogs = []
        
        issue_summary_map = {issue.issue_key: issue.summary for issue in issues}
        issue_keys_set = set(issue.issue_key for issue in issues)
        
        # Fetch worklogs concurrently
        tasks = []
        for issue in issues:
            tasks.append(self._fetch_issue_worklogs(
                issue.issue_key, start_date, end_date, issue_summary_map
            ))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error fetching worklogs: {result}")
            else:
                all_worklogs.extend(result)
        
        logger.info(f"Collected {len(all_worklogs)} worklog entries")
        return all_worklogs
    
    async def _fetch_issue_worklogs(
        self,
        issue_key: str,
        start_date: datetime,
        end_date: datetime,
        issue_summary_map: Dict[str, str]
    ) -> List[WorklogEntry]:
        """Fetch worklogs for a single issue."""
        worklogs = []
        
        try:
            raw_worklogs = await self.jira.get_issue_worklogs(issue_key)
            
            for wl in raw_worklogs:
                started = self._parse_datetime(wl.get("started"))
                if not started:
                    continue
                
                # Filter by date range
                if not (start_date <= started < end_date):
                    continue
                
                account_id, display_name = self._get_display_name(wl.get("author"))
                if not account_id:
                    continue
                
                time_spent_seconds = wl.get("timeSpentSeconds", 0)
                
                comment_adf = wl.get("comment")
                comment = _extract_text_from_adf(comment_adf) if comment_adf else ""
                
                issue_summary = issue_summary_map.get(issue_key, "")
                
                worklog_entry = WorklogEntry(
                    worklog_id=wl["id"],
                    issue_key=issue_key,
                    issue_id=wl.get("issueId", ""),
                    account_id=account_id,
                    display_name=display_name,
                    started=started,
                    time_spent_seconds=time_spent_seconds,
                    time_spent_hours=time_spent_seconds / 3600.0,
                    project_key=issue_key.split("-")[0] if "-" in issue_key else "UNKNOWN",
                    comment=comment if comment else None,
                    issue_summary=issue_summary if issue_summary else None
                )
                worklogs.append(worklog_entry)
                
        except Exception as e:
            logger.error(f"Failed to get worklogs for issue {issue_key}: {e}")
        
        return worklogs
    
    def _calculate_flow_metrics(self, report: ReportData, issues: List[IssueData]):
        """Calculate all flow metrics."""
        # Weekly throughput
        self._calculate_weekly_throughput(report, issues)
        
        # Cycle time data
        self._calculate_cycle_time_data(report, issues)
        
        # Aging WIP
        self._calculate_aging_wip(report, issues)
        
        # Overdue tasks
        self._calculate_overdue(report, issues)
        
        # Reopened tasks
        self._calculate_reopened(report, issues)
        
        # WIP snapshot
        self._calculate_wip_snapshot(report, issues)
        
        # Weekly cycle time
        self._calculate_weekly_cycle_time(report, issues)
        
        # Status distribution
        self._calculate_status_distribution(report, issues)
        
        # Raw transitions
        self._collect_raw_transitions(report, issues)
        
        # Top oldest issues
        self._calculate_top_oldest(report, issues)
        
        # Overall metrics
        report.throughput = sum(wt.closed_tasks_count for wt in report.weekly_throughput)
        
        # Median and P85 cycle time
        cycle_times = [ct.cycle_time_days for ct in report.cycle_time_data if ct.cycle_time_days is not None]
        if cycle_times:
            sorted_ct = sorted(cycle_times)
            report.median_cycle_time = statistics.median(sorted_ct)
            index_85 = int(len(sorted_ct) * 0.85)
            report.p85_cycle_time = sorted_ct[min(index_85, len(sorted_ct) - 1)]
    
    def _calculate_weekly_throughput(self, report: ReportData, issues: List[IssueData]):
        """Calculate weekly throughput."""
        week_ranges = self._get_week_ranges(report.start_date, report.end_date)
        weekly_data = defaultdict(lambda: {"closed": 0, "created": 0})
        
        for week_start, week_end in week_ranges:
            for issue in issues:
                # Count created in week
                if issue.created and week_start <= issue.created < week_end:
                    key = (week_start, week_end, issue.project_key)
                    weekly_data[key]["created"] += 1
                
                # Count closed in week (using status_category_changed_date for done)
                if issue.status_category_changed_date and week_start <= issue.status_category_changed_date < week_end:
                    if issue.status in self.done_statuses:
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
    
    def _calculate_cycle_time_data(self, report: ReportData, issues: List[IssueData]):
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
    
    def _calculate_aging_wip(self, report: ReportData, issues: List[IssueData]):
        """Calculate aging WIP for non-closed issues."""
        now = datetime.now(self.timezone)
        
        for issue in issues:
            if issue.status not in self.done_statuses:
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
    
    def _calculate_overdue(self, report: ReportData, issues: List[IssueData]):
        """Calculate overdue tasks."""
        now = datetime.now(self.timezone)
        
        for issue in issues:
            if issue.due_date and issue.status not in self.done_statuses:
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
    
    def _calculate_reopened(self, report: ReportData, issues: List[IssueData]):
        """Calculate reopened tasks."""
        for issue in issues:
            if issue.reopened_count > 0:
                # Find the last done date and first reopen date
                done_date = None
                reopen_date = None
                
                for trans in issue.transitions:
                    if trans.to_status in self.done_statuses:
                        done_date = trans.transition_date
                    if trans.from_status in self.done_statuses and trans.to_status not in self.done_statuses:
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
    
    def _calculate_wip_snapshot(self, report: ReportData, issues: List[IssueData]):
        """Calculate WIP snapshot (non-closed issues)."""
        report.wip_count = sum(1 for issue in issues if issue.status not in self.done_statuses)
        
        # Also count blocked tasks
        report.blocked_tasks_count = sum(1 for issue in issues if issue.blocked_flag)
    
    def _collect_raw_transitions(self, report: ReportData, issues: List[IssueData]):
        """Collect all raw transitions."""
        for issue in issues:
            report.raw_transitions.extend(issue.transitions)
    
    def _calculate_top_oldest(self, report: ReportData, issues: List[IssueData]):
        """Calculate top 5 oldest non-closed issues."""
        now = datetime.now(self.timezone)
        
        open_issues = [issue for issue in issues if issue.status not in self.done_statuses]
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
    
    def _aggregate_employee_metrics(
        self,
        report: ReportData,
        issues: List[IssueData],
        worklogs: List[WorklogEntry]
    ):
        """Aggregate metrics per employee per project."""
        emp_metrics: Dict[Tuple[str, str], EmployeeMetrics] = {}
        
        # Aggregate worklogs
        for wl in worklogs:
            emp_key = self._get_employee_key(wl.account_id, wl.display_name)
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
            
            emp_key = self._get_employee_key(issue.creator_account_id, issue.creator_display_name)
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
            if issue.status not in self.done_statuses:
                continue
            if not issue.assignee_account_id:
                continue
            
            emp_key = self._get_employee_key(issue.assignee_account_id, issue.assignee_display_name)
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
                emp_key = self._get_employee_key(issue.assignee_account_id, issue.assignee_display_name)
                key = (emp_key, issue.project_key)
                
                if key in emp_metrics:
                    emp_metrics[key].reopened_tasks += 1
        
        # Calculate active WIP per employee
        for issue in issues:
            if issue.status not in self.done_statuses and issue.assignee_account_id:
                emp_key = self._get_employee_key(issue.assignee_account_id, issue.assignee_display_name)
                # Find which project this issue belongs to
                for key in emp_metrics:
                    if key[0] == emp_key and key[1] == issue.project_key:
                        emp_metrics[key].active_wip += 1
                        break
        
        # Calculate overdue per employee
        for issue in issues:
            if issue.overdue_flag and issue.assignee_account_id:
                emp_key = self._get_employee_key(issue.assignee_account_id, issue.assignee_display_name)
                for key in emp_metrics:
                    if key[0] == emp_key and key[1] == issue.project_key:
                        emp_metrics[key].overdue_tasks += 1
                        break
        
        # Calculate cycle time per employee
        employee_cycle_times = defaultdict(list)
        for issue in issues:
            if issue.cycle_time_days is not None and issue.assignee_account_id:
                emp_key = self._get_employee_key(issue.assignee_account_id, issue.assignee_display_name)
                employee_cycle_times[emp_key].append(issue.cycle_time_days)
        
        for key, cycle_times in employee_cycle_times.items():
            if key in emp_metrics:
                emp_metrics[key].avg_cycle_time = sum(cycle_times) / len(cycle_times)
                emp_metrics[key].median_cycle_time = statistics.median(sorted(cycle_times))
        
        report.employee_metrics = list(emp_metrics.values())
    
    async def _filter_employees_by_group(self, report: ReportData, user_group: Optional[str] = None):
        """Filter employee metrics to only include users from the configured Jira group."""
        if not user_group:
            return
        
        try:
            logger.info(f"Fetching members of Jira group: {user_group}")
            group_members = await self.jira.get_group_members(user_group)
            
            # Extract account IDs from group members
            group_account_ids = {member.get("accountId") for member in group_members if member.get("accountId")}
            
            if not group_account_ids:
                logger.warning(f"No members found in group {user_group}")
                return
            
            # Filter employee metrics to only include users in the group
            original_count = len(report.employee_metrics)
            report.employee_metrics = [
                emp for emp in report.employee_metrics
                if emp.account_id in group_account_ids
            ]
            
            filtered_count = original_count - len(report.employee_metrics)
            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} employees not in group '{user_group}'")
            
            logger.info(f"Report now includes {len(report.employee_metrics)} employees from group '{user_group}'")
            
        except Exception as e:
            logger.error(f"Failed to filter employees by group '{user_group}': {e}")
            # Continue without filtering if there's an error
    
    def _aggregate_project_metrics(self, report: ReportData):
        """Aggregate metrics per project."""
        project_data: Dict[str, ProjectMetrics] = {}
        project_employees: Dict[str, set] = defaultdict(set)
        
        for emp in report.employee_metrics:
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
                ct.cycle_time_days for ct in report.cycle_time_data 
                if ct.project_key == proj_key and ct.cycle_time_days is not None
            ]
            if project_cycle_times:
                sorted_ct = sorted(project_cycle_times)
                metrics.median_cycle_time = statistics.median(sorted_ct)
                index_85 = int(len(sorted_ct) * 0.85)
                metrics.p85_cycle_time = sorted_ct[min(index_85, len(sorted_ct) - 1)]
            
            # WIP count for project
            metrics.wip_count = sum(
                1 for aw in report.aging_wip_data if aw.project_key == proj_key
            )
            
            # Aging WIP buckets
            for aw in report.aging_wip_data:
                if aw.project_key == proj_key:
                    if aw.aging_days > 7:
                        metrics.aging_wip_7 += 1
                    if aw.aging_days > 14:
                        metrics.aging_wip_14 += 1
                    if aw.aging_days > 30:
                        metrics.aging_wip_30 += 1
            
            # Reopened tasks
            metrics.reopened_tasks = sum(
                1 for rd in report.reopened_data if rd.project_key == proj_key
            )
            
            # Overdue tasks
            metrics.overdue_tasks = sum(
                1 for od in report.overdue_data if od.project_key == proj_key
            )
            
            # Blocked tasks
            metrics.blocked_tasks = sum(
                1 for issue in report.raw_issues 
                if issue.project_key == proj_key and issue.blocked_flag
            )
        
        report.project_metrics = list(project_data.values())
    
    async def build_custom_report(self, request) -> ReportData:
        """Build report for custom date range with flow metrics."""
        from app.models.schemas import CustomReportRequest
        from datetime import datetime
        
        if isinstance(request, dict):
            request = CustomReportRequest(**request)
        
        project_keys = request.project_keys or settings.project_keys_list
        
        # Get effective user group (from request or ENV)
        user_group = self._get_effective_user_group(request)
        
        # Convert date to datetime with timezone
        # Use exclusive end_date (first moment of next day) for consistency with monthly reports
        start_date = datetime.combine(request.start_date, datetime.min.time()).replace(tzinfo=self.timezone)
        end_date = datetime.combine(request.end_date + timedelta(days=1), datetime.min.time()).replace(tzinfo=self.timezone)
        
        # Use year and month from start_date for ReportData
        report = ReportData(
            year=start_date.year,
            month=start_date.month,
            start_date=start_date,
            end_date=end_date,
            include_raw_data=getattr(request, 'include_raw_data', True)
        )
        
        # Collect all issues with changelog
        all_issues = await self._collect_all_issues_with_changelog(project_keys, start_date, end_date)
        report.raw_issues = all_issues
        
        # Collect all worklogs
        all_worklogs = await self._collect_worklogs(all_issues, start_date, end_date)
        report.raw_worklogs = all_worklogs
        
        # Calculate flow metrics
        self._calculate_flow_metrics(report, all_issues)
        
        # Aggregate employee metrics
        self._aggregate_employee_metrics(report, all_issues, all_worklogs)
        
        # Filter employees by Jira group if configured
        await self._filter_employees_by_group(report, user_group)
        
        # Aggregate project metrics
        self._aggregate_project_metrics(report)
        
        # Calculate totals
        report.total_worklog_hours = sum(em.worklog_hours for em in report.employee_metrics)
        report.total_created_issues = sum(em.created_issues for em in report.employee_metrics)
        report.total_closed_issues = sum(em.closed_issues for em in report.employee_metrics)
        
        return report

    def _calculate_weekly_cycle_time(self, report: ReportData, issues: List[IssueData]):
        """Calculate weekly cycle time (median and P85)."""
        week_ranges = self._get_week_ranges(report.start_date, report.end_date)
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
    
    def _calculate_status_distribution(self, report: ReportData, issues: List[IssueData]):
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
