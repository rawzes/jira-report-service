"""
Builder Data module for Jira Report application.

This module contains methods for collecting data from Jira.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

from app.models.schemas import IssueData, WorklogEntry, IssueTransition
from app.models.config import get_settings

logger = logging.getLogger(__name__)

# Import from parent module to avoid circular imports
# These will be imported at runtime from report_builder


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


async def collect_all_issues_with_changelog(
    jira_client,
    project_keys: List[str],
    start_date: datetime,
    end_date: datetime,
    done_statuses_list: List[str],
    excluded_statuses: List[str]
) -> List[IssueData]:
    """Collect all issues with their changelog history."""
    issues_dict = {}
    
    # Get all issues (created in period or updated in period)
    all_issues_jql = jira_client.build_all_issues_jql(project_keys, start_date, end_date)
    logger.info(f"Fetching all issues with JQL: {all_issues_jql}")
    
    issue_keys = []
    async for issues_page in jira_client.search_issues_jql(
        all_issues_jql,
        fields=["key"]
    ):
        for issue in issues_page:
            issue_keys.append(issue["key"])
    
    logger.info(f"Found {len(issue_keys)} issues to fetch with changelog")
    
    # Fetch each issue with changelog concurrently
    tasks = []
    for issue_key in issue_keys:
        tasks.append(_fetch_issue_with_changelog(jira_client, issue_key, done_statuses_list, excluded_statuses))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Error fetching issue with changelog: {result}")
        elif result:
            issues_dict[result.issue_key] = result
    
    issues = list(issues_dict.values())
    
    # Filter excluded statuses
    if excluded_statuses:
        filtered_issues = [issue for issue in issues if issue.status not in excluded_statuses]
        excluded_count = len(issues) - len(filtered_issues)
        if excluded_count > 0:
            logger.info(f"Filtered out {excluded_count} issues with excluded statuses: {excluded_statuses}")
        return filtered_issues
    
    return issues


async def _fetch_issue_with_changelog(
    jira_client,
    issue_key: str,
    done_statuses: List[str],
    excluded_statuses: List[str]
) -> Optional[IssueData]:
    """Fetch a single issue with its complete changelog."""
    try:
        issue_data = await jira_client.get_issue_changelog(issue_key)
        return _parse_issue_from_changelog(issue_data, done_statuses, excluded_statuses)
    except Exception as e:
        logger.error(f"Failed to fetch issue {issue_key} with changelog: {e}")
        return None


def _parse_issue_from_changelog(
    issue_data: Dict,
    done_statuses: List[str],
    start_statuses: List[str] = None,
    blocked_statuses: List[str] = None
) -> IssueData:
    """Parse issue data including changelog to extract flow metrics."""
    fields = issue_data.get("fields", {})
    changelog = issue_data.get("changelog", {})
    histories = changelog.get("histories", [])
    
    project = fields.get("project", {})
    project_key = project.get("key", "UNKNOWN")
    
    creator_account_id, creator_display_name = _get_display_name(fields.get("creator"))
    assignee_account_id, assignee_display_name = _get_display_name(fields.get("assignee"))
    
    created = _parse_datetime(fields.get("created"))
    resolution_date = _parse_datetime(fields.get("resolutiondate"))
    
    issue_key = issue_data.get("key", "")
    issue_id = issue_data.get("id", "")
    issue_type = fields.get("issuetype", {}).get("name", "")
    summary = fields.get("summary", "")
    status = fields.get("status", {}).get("name", "")
    reporter = fields.get("reporter", {}).get("displayName") if fields.get("reporter") else None
    due_date = _parse_datetime(fields.get("duedate"))
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
        history_date = _parse_datetime(history.get("created"))
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
                if start_statuses and to_status in start_statuses and start_progress_date is None:
                    start_progress_date = history_date
                
                # Check for done status
                if to_status in done_statuses:
                    done_date = history_date
                    was_done = True
                
                # Check for reopen (from done to non-done)
                if from_status in done_statuses and to_status not in done_statuses:
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
    blocked_flag = status in blocked_statuses if blocked_statuses else False
    
    # Check if overdue
    overdue_flag = False
    if due_date and not done_date:
        overdue_flag = datetime.now().astimezone() > due_date
    
    # Calculate aging days
    aging_days = None
    if not done_date and created:
        aging_days = (datetime.now().astimezone() - created).days
    
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


async def collect_worklogs(
    jira_client,
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
        tasks.append(_fetch_issue_worklogs(
            jira_client, issue.issue_key, start_date, end_date, issue_summary_map
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
    jira_client,
    issue_key: str,
    start_date: datetime,
    end_date: datetime,
    issue_summary_map: Dict[str, str]
) -> List[WorklogEntry]:
    """Fetch worklogs for a single issue."""
    worklogs = []
    
    try:
        raw_worklogs = await jira_client.get_issue_worklogs(issue_key)
        
        for wl in raw_worklogs:
            started = _parse_datetime(wl.get("started"))
            if not started:
                continue
            
            # Filter by date range
            if not (start_date <= started < end_date):
                continue
            
            account_id, display_name = _get_display_name(wl.get("author"))
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


def _get_display_name(user_obj: Optional[Dict]) -> Tuple[Optional[str], Optional[str]]:
    """Extract account_id and display_name from Jira user object."""
    if not user_obj:
        return None, None
    
    if user_obj.get("accountId") is None and user_obj.get("displayName"):
        return "deleted", user_obj.get("displayName", "Deleted User")
    
    return user_obj.get("accountId"), user_obj.get("displayName")


def _parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """Parse Jira datetime string to datetime with timezone."""
    if not date_str:
        return None
    try:
        from zoneinfo import ZoneInfo
        settings = get_settings()
        timezone = ZoneInfo(settings.TIMEZONE)
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.astimezone(timezone)
    except Exception as e:
        logger.warning(f"Failed to parse datetime '{date_str}': {e}")
        return None
