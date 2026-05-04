from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date


class MonthlyReportRequest(BaseModel):
    """Request model for monthly report generation."""
    
    year: int
    month: int
    project_keys: Optional[List[str]] = None
    group_by_projects: bool = True
    include_raw_data: bool = True


class CustomReportRequest(BaseModel):
    """Request model for custom date range report generation."""
    
    start_date: date
    end_date: date
    project_keys: Optional[List[str]] = None
    group_by_projects: bool = True
    include_raw_data: bool = True


class WorklogEntry(BaseModel):
    """Worklog entry data."""
    
    worklog_id: str
    issue_key: str
    issue_id: str
    account_id: str
    display_name: str
    started: datetime
    time_spent_seconds: int
    time_spent_hours: float
    project_key: str
    comment: Optional[str] = None
    issue_summary: Optional[str] = None


class IssueTransition(BaseModel):
    """Issue status transition data."""
    
    issue_key: str
    project_key: str
    from_status: str
    to_status: str
    transition_date: datetime
    transition_author: Optional[str] = None


class IssueData(BaseModel):
    """Issue data for reporting."""
    
    issue_key: str
    issue_id: str
    project_key: str
    issue_type: Optional[str] = None
    summary: str
    status: str
    created: datetime
    creator_account_id: Optional[str] = None
    creator_display_name: Optional[str] = None
    assignee_account_id: Optional[str] = None
    assignee_display_name: Optional[str] = None
    reporter: Optional[str] = None
    resolution_date: Optional[datetime] = None
    status_category_changed_date: Optional[datetime] = None
    # Flow metrics
    start_progress_date: Optional[datetime] = None
    cycle_time_days: Optional[float] = None
    cycle_time_hours: Optional[float] = None
    reopened_count: int = 0
    reopened_flag: bool = False
    blocked_flag: bool = False
    overdue_flag: bool = False
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    aging_days: Optional[int] = None
    # Transitions for detailed analysis
    transitions: List[IssueTransition] = []
    last_status_change_date: Optional[datetime] = None


class EmployeeMetrics(BaseModel):
    """Metrics aggregated per employee."""
    
    account_id: str
    display_name: str
    project_key: str
    worklog_hours: float = 0.0
    created_issues: int = 0
    closed_issues: int = 0
    reopened_tasks: int = 0
    active_wip: int = 0
    avg_cycle_time: Optional[float] = None
    median_cycle_time: Optional[float] = None
    overdue_tasks: int = 0


class ProjectMetrics(BaseModel):
    """Metrics aggregated per project."""
    
    project_key: str
    worklog_hours: float = 0.0
    created_issues: int = 0
    closed_issues: int = 0
    employee_count: int = 0
    throughput: int = 0
    median_cycle_time: Optional[float] = None
    p85_cycle_time: Optional[float] = None
    wip_count: int = 0
    aging_wip_7: int = 0
    aging_wip_14: int = 0
    aging_wip_30: int = 0
    reopened_tasks: int = 0
    overdue_tasks: int = 0
    blocked_tasks: int = 0


class WeeklyThroughput(BaseModel):
    """Weekly throughput data."""
    
    week_start: datetime
    week_end: datetime
    project_key: str
    closed_tasks_count: int = 0
    created_tasks_count: int = 0
    net_flow: int = 0


class CycleTimeData(BaseModel):
    """Cycle time data for an issue."""
    
    issue_key: str
    project_key: str
    issue_type: Optional[str] = None
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    start_progress_date: Optional[datetime] = None
    done_date: Optional[datetime] = None
    cycle_time_days: Optional[float] = None
    cycle_time_hours: Optional[float] = None
    reopened_flag: bool = False


class AgingWipData(BaseModel):
    """Aging WIP data for an issue."""
    
    issue_key: str
    project_key: str
    status: str
    assignee: Optional[str] = None
    created_date: datetime
    last_status_change_date: Optional[datetime] = None
    aging_days: int = 0
    blocked_flag: bool = False
    due_date: Optional[datetime] = None
    overdue_flag: bool = False


class OverdueData(BaseModel):
    """Overdue task data."""
    
    issue_key: str
    project_key: str
    assignee: Optional[str] = None
    status: str
    due_date: datetime
    days_overdue: int = 0
    priority: Optional[str] = None


class ReopenedData(BaseModel):
    """Reopened task data."""
    
    issue_key: str
    project_key: str
    assignee: Optional[str] = None
    done_date: Optional[datetime] = None
    reopen_date: Optional[datetime] = None
    reopen_count: int = 0
    current_status: str = ""


class RiskFlag(BaseModel):
    """Risk flag data."""
    
    risk_type: str
    description: str
    severity: str = "medium"  # low, medium, high
    issue_keys: List[str] = []
    project_key: Optional[str] = None
    employee_name: Optional[str] = None


class ReportData(BaseModel):
    """Complete report data structure."""
    
    year: int
    month: int
    start_date: datetime
    end_date: datetime
    
    # Basic metrics
    employee_metrics: List[EmployeeMetrics] = []
    project_metrics: List[ProjectMetrics] = []
    total_worklog_hours: float = 0.0
    total_created_issues: int = 0
    total_closed_issues: int = 0
    
    # Flow metrics
    throughput: int = 0
    median_cycle_time: Optional[float] = None
    p85_cycle_time: Optional[float] = None
    wip_count: int = 0
    aging_wip_count: int = 0
    overdue_tasks_count: int = 0
    reopened_tasks_count: int = 0
    blocked_tasks_count: int = 0
    
    # Detailed data for sheets
    weekly_throughput: List[WeeklyThroughput] = []
    cycle_time_data: List[CycleTimeData] = []
    aging_wip_data: List[AgingWipData] = []
    overdue_data: List[OverdueData] = []
    reopened_data: List[ReopenedData] = []
    
    # Raw data
    raw_issues: List[IssueData] = []
    raw_worklogs: List[WorklogEntry] = []
    raw_transitions: List[IssueTransition] = []
    
    # Risk flags
    risk_flags: List[RiskFlag] = []
    
    # Top oldest open issues
    top_oldest_issues: List[Dict[str, Any]] = []
    
    # Include raw data flag
    include_raw_data: bool = True


class WeeklyCycleTime(BaseModel):
    """Weekly cycle time data."""
    
    week_start: datetime
    week_end: datetime
    project_key: str
    median_cycle_time: Optional[float] = None
    p85_cycle_time: Optional[float] = None
    tasks_count: int = 0


class StatusDistribution(BaseModel):
    """Status distribution by project."""
    
    project_key: str
    status: str
    count: int = 0


class ReportData(BaseModel):
    """Complete report data structure."""
    
    year: int
    month: int
    start_date: datetime
    end_date: datetime
    
    # Basic metrics
    employee_metrics: List[EmployeeMetrics] = []
    project_metrics: List[ProjectMetrics] = []
    total_worklog_hours: float = 0.0
    total_created_issues: int = 0
    total_closed_issues: int = 0
    
    # Flow metrics
    throughput: int = 0
    median_cycle_time: Optional[float] = None
    p85_cycle_time: Optional[float] = None
    wip_count: int = 0
    aging_wip_count: int = 0
    overdue_tasks_count: int = 0
    reopened_tasks_count: int = 0
    blocked_tasks_count: int = 0
    
    # Detailed data for sheets
    weekly_throughput: List[WeeklyThroughput] = []
    weekly_cycle_time: List[WeeklyCycleTime] = []
    cycle_time_data: List[CycleTimeData] = []
    aging_wip_data: List[AgingWipData] = []
    overdue_data: List[OverdueData] = []
    reopened_data: List[ReopenedData] = []
    status_distribution: List[StatusDistribution] = []
    
    # Raw data
    raw_issues: List[IssueData] = []
    raw_worklogs: List[WorklogEntry] = []
    raw_transitions: List[IssueTransition] = []
    
    # Risk flags
    risk_flags: List[RiskFlag] = []
    
    # Top oldest open issues
    top_oldest_issues: List[Dict[str, Any]] = []
    
    # Include raw data flag
    include_raw_data: bool = True
