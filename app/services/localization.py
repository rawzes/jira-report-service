"""
Localization module for Jira Report application.

This module contains all user-facing strings in both English (en) and Russian (ru).
Use the get_localization(lang) function to get the appropriate dictionary.
"""

# Localization strings
LOCALIZATION = {
    "en": {
        # Navigation tabs
        "summary": "Summary",
        "by_employee": "By Employee",
        "by_project": "By Project",
        "charts": "Charts",
        
        # Section headers
        "weekly_throughput": "Weekly Throughput",
        "cycle_time": "Cycle Time",
        "aging_wip": "Aging WIP",
        "overdue": "Overdue",
        "reopened": "Reopened",
        "raw_issues": "Raw Issues",
        "raw_worklogs": "Raw Worklogs",
        "raw_transitions": "Raw Transitions",
        
        # Summary section
        "metric": "Metric",
        "value": "Value",
        "report_period": "Report Period",
        "total_worklog_hours": "Total Worklog Hours",
        "total_created_issues": "Total Created Issues",
        "total_closed_issues": "Total Closed Issues",
        "throughput": "Throughput",
        "median_cycle_time": "Median Cycle Time (days)",
        "p85_cycle_time": "85th Percentile Cycle Time (days)",
        "overdue_tasks": "Overdue Tasks",
        "reopened_tasks": "Reopened Tasks",
        "blocked_tasks": "Blocked Tasks",
        "top_oldest_issues": "Top 5 Oldest Open Issues",
        
        # Table headers
        "issue_key": "Issue Key",
        "project_key": "Project Key",
        "status": "Status",
        "created": "Created",
        "aging_days": "Aging (days)",
        "assignee": "Assignee",
        "employee_name": "Employee Name",
        "account_id": "Account ID",
        "worklog_hours": "Worklog Hours",
        "created_issues": "Created Issues",
        "closed_issues": "Closed Issues",
        "reopen_count": "Reopened Count",
        "active_wip": "Active WIP",
        "avg_cycle_time": "Avg Cycle Time",
        "overdue_count": "Overdue Count",
        "project": "Project",
        "throughput_count": "Throughput",
        "wip_count": "WIP Count",
        "aging_7": "Aging >7 days",
        "aging_14": "Aging >14 days",
        "aging_30": "Aging >30 days",
        "blocked_count": "Blocked Count",
        
        # Weekly throughput
        "week_start": "Week Start",
        "week_end": "Week End",
        "created_count": "Created Count",
        "closed_count": "Closed Count",
        "net_flow": "Net Flow",
        
        # Issue details
        "issue_type": "Issue Type",
        "reporter": "Reporter",
        "start_progress_date": "Start Progress Date",
        "done_date": "Done Date",
        "cycle_time_days": "Cycle Time (days)",
        "cycle_time_hours": "Cycle Time (hours)",
        "reopened_flag": "Reopened?",
        "last_status_change": "Last Status Change",
        "blocked_flag": "Blocked?",
        "due_date": "Due Date",
        "overdue_flag": "Overdue?",
        "priority": "Priority",
        "days_overdue": "Days Overdue",
        "reopen_date": "Reopen Date",
        "current_status": "Current Status",
        
        # Transitions
        "from_status": "From Status",
        "to_status": "To Status",
        "transition_date": "Transition Date",
        "transition_author": "Transition Author",
        
        # Worklogs
        "started": "Started",
        "time_spent_hours": "Time Spent (hours)",
        "comment": "Comment",
        
        # Totals
        "total": "TOTAL",
        
        # Chart titles
        "cycle_time_by_week": "Cycle Time by Week",
        "status_by_project": "Status by Project",
        "closed_by_week": "Closed Tasks by Week",
        "worklog_by_employee": "Worklog by Employee",
        "aging_buckets": "Aging WIP Buckets",
        "reopened_by_project": "Reopened by Project",
        
        # Report
        "report_title": "Report for period",
        "report_header": "Report for period",
        "download_report": "Download Report",
    },
    "ru": {
        # Navigation tabs
        "summary": "Сводка",
        "by_employee": "По сотрудникам",
        "by_project": "По проектам",
        "charts": "Графики",
        
        # Section headers
        "weekly_throughput": "Недельный поток",
        "cycle_time": "Время цикла",
        "aging_wip": "Старые WIP",
        "overdue": "Просроченные",
        "reopened": "Переоткрытые",
        "raw_issues": "Сырые данные задач",
        "raw_worklogs": "Сырые данные трудозатрат",
        "raw_transitions": "Сырые данные переходов",
        
        # Summary section
        "metric": "Показатель",
        "value": "Значение",
        "report_period": "Период отчета",
        "total_worklog_hours": "Всего часов трудозатрат",
        "total_created_issues": "Всего создано задач",
        "total_closed_issues": "Всего закрыто задач",
        "throughput": "Поток",
        "median_cycle_time": "Медиана времени цикла (дни)",
        "p85_cycle_time": "85-й перцентиль времени цикла (дни)",
        "overdue_tasks": "Просроченные задачи",
        "reopened_tasks": "Переоткрытые задачи",
        "blocked_tasks": "Заблокированные задачи",
        "top_oldest_issues": "Топ-5 самых старых открытых задач",
        
        # Table headers
        "issue_key": "Ключ задачи",
        "project_key": "Проект",
        "status": "Статус",
        "created": "Создана",
        "aging_days": "Возраст (дни)",
        "assignee": "Исполнитель",
        "employee_name": "Сотрудник",
        "account_id": "ID аккаунта",
        "worklog_hours": "Часы трудозатрат",
        "created_issues": "Создано задач",
        "closed_issues": "Закрыто задач",
        "reopen_count": "Кол-во переоткрытий",
        "active_wip": "Активный WIP",
        "avg_cycle_time": "Среднее время цикла",
        "overdue_count": "Просрочено",
        "project": "Проект",
        "throughput_count": "Поток",
        "wip_count": "WIP",
        "aging_7": "Возраст >7 дней",
        "aging_14": "Возраст >14 дней",
        "aging_30": "Возраст >30 дней",
        "blocked_count": "Заблокировано",
        
        # Weekly throughput
        "week_start": "Начало недели",
        "week_end": "Конец недели",
        "created_count": "Создано",
        "closed_count": "Закрыто",
        "net_flow": "Чистый поток",
        
        # Issue details
        "issue_type": "Тип задачи",
        "reporter": "Репортер",
        "start_progress_date": "Дата начала работы",
        "done_date": "Дата завершения",
        "cycle_time_days": "Время цикла (дни)",
        "cycle_time_hours": "Время цикла (часы)",
        "reopened_flag": "Переоткрыта?",
        "last_status_change": "Последний переход",
        "blocked_flag": "Заблокирована?",
        "due_date": "Срок",
        "overdue_flag": "Просрочена?",
        "priority": "Приоритет",
        "days_overdue": "Дней просрочки",
        "reopen_date": "Дата переоткрытия",
        "current_status": "Текущий статус",
        
        # Transitions
        "from_status": "Из статуса",
        "to_status": "В статус",
        "transition_date": "Дата перехода",
        "transition_author": "Автор перехода",
        
        # Worklogs
        "started": "Начало",
        "time_spent_hours": "Часы",
        "comment": "Комментарий",
        
        # Totals
        "total": "ИТОГО",
        
        # Chart titles
        "cycle_time_by_week": "Время цикла по неделям",
        "status_by_project": "Статусы по проектам",
        "closed_by_week": "Закрытые задачи по неделям",
        "worklog_by_employee": "Трудозатраты по сотрудникам",
        "aging_buckets": "Возрастные группы WIP",
        "reopened_by_project": "Переоткрытые по проектам",
        
        # Report
        "report_title": "Отчет за период",
        "report_header": "Отчет за период",
        "download_report": "Скачать отчет",
    }
}


def get_localization(lang: str = "en") -> dict:
    """
    Get the localization dictionary for the specified language.
    
    Args:
        lang: Language code ('en' or 'ru')
        
    Returns:
        Dictionary with localized strings
    """
    if lang not in LOCALIZATION:
        lang = "en"  # Default to English
    return LOCALIZATION[lang]
