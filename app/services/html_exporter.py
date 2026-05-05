import logging
from typing import List, Optional, Dict
from datetime import datetime
from io import BytesIO
from collections import defaultdict
import base64
from urllib.parse import quote

from app.models.schemas import (
    ReportData, EmployeeMetrics, ProjectMetrics, 
    IssueData, WorklogEntry, IssueTransition,
    WeeklyThroughput, WeeklyCycleTime, CycleTimeData, AgingWipData,
    OverdueData, ReopenedData, StatusDistribution
)
from app.models.config import get_settings

logger = logging.getLogger(__name__)


class HtmlExporter:
    """Generates HTML reports with embedded charts."""
    
    def __init__(self, lang: str = None):
        self.settings = get_settings()
        self.lang = lang or self.settings.REPORT_LANG
        if self.lang not in LOCALIZATION:
            self.lang = "en"
        self._ = LOCALIZATION[self.lang]
        self.jira_base = self.settings.JIRA_BASE_URL.rstrip('/')
        
    def generate(self, report: ReportData) -> str:
        """Generate HTML report with all data and embedded charts."""
        logger.info("Starting HTML report generation")
        try:
            # Build JIRA filter URLs for summary links
            logger.debug("Building project keys and date strings")
            project_keys = ','.join([f'"{p.project_key}"' for p in report.project_metrics]) if report.project_metrics else ''
            start_str = report.start_date.strftime('%Y-%m-%d')
            end_str = report.end_date.strftime('%Y-%m-%d')
            
            # Build JQL filter URLs
            logger.debug("Building JQL filter URLs")
            created_jql = f"project in ({project_keys}) AND created >= '{start_str}' AND created < '{end_str}'"
            closed_jql = f"project in ({project_keys}) AND status in ({",".join([f'"{s}"' for s in self.settings.done_statuses_list])}) AND status changed to Done during ('{start_str}', '{end_str}')"
            overdue_jql = f"project in ({project_keys}) AND duedate < now() AND status not in ({",".join([f'"{s}"' for s in self.settings.done_statuses_list])})"
            reopened_jql = f"project in ({project_keys}) AND status changed from Done to * during ('{start_str}', '{end_str}')"
            blocked_jql = f"project in ({project_keys}) AND status in ({",".join([f'"{s}"' for s in self.settings.blocked_statuses_list])})"
            
            logger.debug("Building HTML structure with logging")
            html_parts = []
            
            # HTML header
            logger.debug("Adding HTML header")
            interval_str = f"{report.start_date.strftime('%Y-%m-%d')} - {report.end_date.strftime('%Y-%m-%d')}"
            
            
            html_parts.append(f"""<!DOCTYPE html>
<html lang="{self.lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчет за месяц {interval_str}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
""")
            
            # CSS
            logger.debug("Generating CSS")
            html_parts.append(self._get_css())
            html_parts.append("""    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Отчет за месяц</h1>
        <p class="subtitle">""" + interval_str + """</p>
        <button id="downloadBtn" class="download-btn" onclick="downloadReport()">📥 Скачать отчет</button>
""")
            
            # Summary section
            logger.debug("Generating summary section")
            html_parts.append(self._generate_summary_section(report, created_jql, closed_jql, overdue_jql, reopened_jql, blocked_jql))
            
            # Tab navigation
            logger.debug("Adding tab navigation")
            html_parts.append(f"""
        <div class="tab-navigation">
            <button class="tab-button active" data-tab="by-employee">{self._["by_employee"]}</button>
            <button class="tab-button" data-tab="employee-worklog-summary">{self._get("worklog_by_employee", "Worklog by Employee")}</button>
            <button class="tab-button" data-tab="by-project">{self._["by_project"]}</button>
            <button class="tab-button" data-tab="weekly-data">{self._["weekly_throughput"]}</button>
            <button class="tab-button" data-tab="cycle-time">{self._["cycle_time"]}</button>
            <button class="tab-button" data-tab="aging-wip">{self._["aging_wip"]}</button>
            <button class="tab-button" data-tab="overdue">{self._["overdue"]}</button>
            <button class="tab-button" data-tab="reopened">{self._["reopened"]}</button>
            <button class="tab-button" data-tab="charts">{self._["charts"]}</button>
            <button class="tab-button" data-tab="raw-data">{self._["raw_issues"]}</button>
        </div>
""")
            
            # Tab contents with individual logging
            logger.debug("Generating by-employee section")
            html_parts.append("""        <div id="by-employee" class="tab-content active">""")
            html_parts.append(self._generate_by_employee_section(report))
            html_parts.append("""        </div>""")
            
            logger.debug("Generating by-project section")
            
            # Employee worklog summary section
            logger.debug("Generating employee worklog summary section")
            html_parts.append("""        <div id="employee-worklog-summary" class="tab-content">""")
            html_parts.append(self._generate_employee_worklog_summary_section(report))
            html_parts.append("""        </div>""")
            html_parts.append("""        <div id="by-project" class="tab-content">""")
            html_parts.append(self._generate_by_project_section(report))
            html_parts.append("""        </div>""")
            
            logger.debug("Generating weekly-throughput section")
            html_parts.append("""        <div id="weekly-data" class="tab-content">""")
            html_parts.append(self._generate_weekly_throughput_section(report))
            html_parts.append("""        </div>""")
            
            logger.debug("Generating cycle-time section")
            html_parts.append("""        <div id="cycle-time" class="tab-content">""")
            html_parts.append(self._generate_cycle_time_section(report))
            html_parts.append("""        </div>""")
            
            logger.debug("Generating aging-wip section")
            html_parts.append("""        <div id="aging-wip" class="tab-content">""")
            html_parts.append(self._generate_aging_wip_section(report))
            html_parts.append("""        </div>""")
            
            logger.debug("Generating overdue section")
            html_parts.append("""        <div id="overdue" class="tab-content">""")
            html_parts.append(self._generate_overdue_section(report))
            html_parts.append("""        </div>""")
            
            logger.debug("Generating reopened section")
            html_parts.append("""        <div id="reopened" class="tab-content">""")
            html_parts.append(self._generate_reopened_section(report))
            html_parts.append("""        </div>""")
            
            logger.debug("Generating charts section")
            html_parts.append("""        <div id="charts" class="tab-content">""")
            html_parts.append(self._generate_charts_section(report))
            html_parts.append("""        </div>""")
            
            logger.debug("Generating raw-data section")
            html_parts.append("""        <div id="raw-data" class="tab-content">""")
            if report.include_raw_data:
                html_parts.append(self._generate_raw_data_sections(report))
            html_parts.append("""        </div>""")
            
            # JavaScript
            logger.debug("Adding JavaScript")
            html_parts.append("""
    </div>
    
    <script>
        // Tab navigation with smooth transitions
        document.querySelectorAll('.tab-button').forEach(function(button) {
            button.addEventListener('click', function() {
                // Remove active class from all buttons and contents
                document.querySelectorAll('.tab-button').forEach(function(b) { b.classList.remove('active'); });
                document.querySelectorAll('.tab-content').forEach(function(c) {
                    c.classList.remove('active');
                });
                
                // Add active class to clicked button and corresponding content
                button.classList.add('active');
                const tabId = button.getAttribute('data-tab');
                const targetContent = document.getElementById(tabId);
                targetContent.classList.add('active');
            });
        });
    </script>
</body>
</html>
""")
            
            logger.info("HTML report generation completed successfully")
            return ''.join(html_parts)
            
        except Exception as e:
            logger.error(f"Error generating HTML report: {e}", exc_info=True)
            raise
    
    def _get_css(self) -> str:
        """Return CSS styles for the HTML report."""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            padding: 40px;
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 32px;
        }
        .subtitle {
            color: #7f8c8d;
            margin-bottom: 30px;
            font-size: 16px;
        }
        .share-link {
            background: #e8f4f8;
            border: 1px solid #3498db;
            border-radius: 6px;
            padding: 10px 15px;
            margin-bottom: 20px;
            font-size: 14px;
            word-break: break-all;
        }
        .share-link a {
            color: #3498db;
            text-decoration: none;
        }
        .share-link a:hover {
            text-decoration: underline;
        }
        h2 {
            color: #34495e;
            margin-top: 40px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #3498db;
            font-size: 24px;
        }
        h3 {
            color: #555;
            margin-top: 20px;
            margin-bottom: 15px;
            font-size: 18px;
        }
        
        /* Tab Navigation */
        .tab-navigation {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 20px 0 30px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .tab-button {
            padding: 10px 18px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            color: #555;
            transition: all 0.3s;
        }
        .tab-button:hover {
            background: #e8f4f8;
            border-color: #3498db;
            transform: translateY(-1px);
        }
        .tab-button.active {
            background: #3498db;
            color: white;
            border-color: #3498db;
            box-shadow: 0 2px 4px rgba(52, 152, 219, 0.3);
        }
        .tab-content {
            display: none;
            opacity: 0;
            transition: opacity 0.3s ease-in;
        }
        .tab-content.active {
            display: block;
            opacity: 1;
            animation: fadeIn 0.3s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Table Responsive Wrapper with improved styling */
        .table-responsive {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            border: 1px solid #e0e0e0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            min-width: 800px;
        }
        th {
            background: #3498db;
            color: white;
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            white-space: nowrap;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        td {
            padding: 12px 16px;
            border-bottom: 1px solid #ecf0f1;
            font-size: 13px;
            max-width: 250px;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        tr:nth-child(even) {
            background: #f8f9fa;
        }
        tr:hover {
            background: #e8f4f8;
            transition: background 0.2s;
        }
        .total-row {
            font-weight: bold;
            background: #d0d0d0 !important;
        }
        a {
            color: #3498db;
            text-decoration: none;
            transition: color 0.2s;
        }
        a:hover {
            text-decoration: underline;
            color: #2980b9;
        }
        .metric-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            border-left: 4px solid #3498db;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .metric-label {
            color: #7f8c8d;
            font-size: 14px;
            margin-bottom: 5px;
        }
        .metric-value {
            color: #2c3e50;
            font-size: 28px;
            font-weight: bold;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .chart-container {
            width: 100%;
            max-width: 900px;
            height: 450px;
            margin: 20px 0;
            position: relative;
        }
        .chart-container canvas {
            width: 100% !important;
            height: 100% !important;
        }
        .no-data {
            color: #7f8c8d;
            font-style: italic;
            padding: 20px;
            text-align: center;
        }
        
        /* Responsive improvements */
        @media (max-width: 768px) {
            .container {
                padding: 20px;
            }
            h1 {
                font-size: 24px;
            }
            .tab-button {
                padding: 8px 12px;
                font-size: 12px;
            }
            .metrics-grid {
                grid-template-columns: 1fr;
            }
            table {
                min-width: 600px;
            }
        }
        
        /* Download button */
        .download-btn {
            background: #3498db;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            margin: 20px 0;
            transition: all 0.3s;
            display: inline-block;
        }
        .download-btn:hover {
            background: #2980b9;
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(52, 152, 219, 0.4);
        }
"""
    
    def _generate_jira_link(self, jql: str, text: str) -> str:
        """Generate a JIRA filter link."""
        encoded_jql = quote(jql, safe='')
        return f'<a href="{self.jira_base}/issues/?jql={encoded_jql}" target="_blank">{text}</a>'
    
    def _generate_summary_section(self, report: ReportData, created_jql: str, closed_jql: str, 
                                   overdue_jql: str, reopened_jql: str, blocked_jql: str) -> str:
        """Generate summary section with JIRA links and navigation."""
        html = f"<h2>{self._['summary']}</h2>"
        
        html += '<div class="metrics-grid">'
        
        metrics = [
            (self._["total_worklog_hours"], f"{report.total_worklog_hours:.2f}"),
            (self._["total_created_issues"], self._generate_jira_link(created_jql, str(report.total_created_issues))),
            (self._["total_closed_issues"], self._generate_jira_link(closed_jql, str(report.total_closed_issues))),
            (self._["throughput"], str(report.throughput)),
            (self._["median_cycle_time"], f"{report.median_cycle_time:.2f}" if report.median_cycle_time else "N/A"),
            (self._["p85_cycle_time"], f"{report.p85_cycle_time:.2f}" if report.p85_cycle_time else "N/A"),
            (self._["overdue_tasks"], self._generate_jira_link(overdue_jql, str(report.overdue_tasks_count))),
            (self._["reopened_tasks"], self._generate_jira_link(reopened_jql, str(report.reopened_tasks_count))),
            (self._["blocked_tasks"], self._generate_jira_link(blocked_jql, str(report.blocked_tasks_count))),
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
            html += f"<h3>{self._['top_oldest_issues']}</h3>"
            html += "<div class='table-responsive'><table><thead><tr>"
            for header in [self._["issue_key"], self._["summary"], self._["project_key"], 
                          self._["status"], self._["aging_days"], self._["assignee"]]:
                html += f"<th>{header}</th>"
            html += "</tr></thead><tbody>"
            
            for issue in report.top_oldest_issues:
                issue_key = issue.get('issue_key', '')
                html += "<tr>"
                html += f"<td><a href='{self.jira_base}/browse/{issue_key}' target='_blank'>{issue_key}</a></td>"
                html += f"<td>{issue.get('summary', '')}</td>"
                html += f"<td>{issue.get('project_key', '')}</td>"
                html += f"<td>{issue.get('status', '')}</td>"
                html += f"<td>{issue.get('aging_days', 0)}</td>"
                html += f"<td>{issue.get('assignee', '')}</td>"
                html += "</tr>"
            
            html += "</tbody></table></div>"
        
        return html
    
    def _generate_by_employee_section(self, report: ReportData) -> str:
        """Generate by employee section - Account ID hidden."""
        if not report.employee_metrics:
            return ""
        
        html = f"<h2>{self._['by_employee']}</h2>"
        html += "<div class='table-responsive'><table><thead><tr>"
        # Removed account_id from headers
        for header in [self._["employee_name"], self._["project_key"],
                      self._["worklog_hours"], self._["created_issues"], self._["closed_issues"],
                      self._["reopen_count"], self._["active_wip"], self._["avg_cycle_time"],
                      self._["median_cycle_time"], self._["overdue_count"]]:
            html += f"<th>{header}</th>"
        html += "</tr></thead><tbody>"
        
        for emp in report.employee_metrics:
            html += "<tr>"
            html += f"<td>{emp.display_name}</td>"
            # Account ID hidden
            html += f"<td><a href='{self.jira_base}/projects/{emp.project_key}' target='_blank'>{emp.project_key}</a></td>"
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
        html += f"<td>{self._['total']}</td><td></td>"
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
    
    def _generate_by_project_section(self, report: ReportData) -> str:
        """Generate by project section with responsive wrapper."""
        if not report.project_metrics:
            return ""
        
        html = f"<h2>{self._['by_project']}</h2>"
        html += "<div class='table-responsive'><table><thead><tr>"
        for header in [self._["project_key"], self._["worklog_hours"], self._["created_issues"],
                      self._["closed_issues"], self._["throughput_count"], self._["median_cycle_time"],
                      self._["p85_cycle_time"], self._["wip_count"], self._["aging_7"],
                      self._["aging_14"], self._["aging_30"], self._["reopen_count"],
                      self._["overdue_count"], self._["blocked_count"]]:
            html += f"<th>{header}</th>"
        html += "</tr></thead><tbody>"
        
        for proj in report.project_metrics:
            html += "<tr>"
            html += f"<td><a href='{self.jira_base}/projects/{proj.project_key}' target='_blank'>{proj.project_key}</a></td>"
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
        html += f"<td>{self._['total']}</td>"
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
    
    def _generate_weekly_throughput_section(self, report: ReportData) -> str:
        """Generate weekly throughput section with responsive wrapper."""
        if not report.weekly_throughput:
            return ""
        
        html = f"<h2>{self._['weekly_throughput']}</h2>"
        html += "<div class='table-responsive'><table><thead><tr>"
        for header in [self._["week_start"], self._["week_end"], self._["project_key"],
                      self._["closed_count"], self._["created_count"], self._["net_flow"]]:
            html += f"<th>{header}</th>"
        html += "</tr></thead><tbody>"
        
        for wt in report.weekly_throughput:
            html += "<tr>"
            html += f"<td>{wt.week_start.strftime('%Y-%m-%d')}</td>"
            html += f"<td>{wt.week_end.strftime('%Y-%m-%d')}</td>"
            html += f"<td><a href='{self.jira_base}/projects/{wt.project_key}' target='_blank'>{wt.project_key}</a></td>"
            html += f"<td>{wt.closed_tasks_count}</td>"
            html += f"<td>{wt.created_tasks_count}</td>"
            html += f"<td>{wt.net_flow}</td>"
            html += "</tr>"
        
        html += "</tbody></table></div>"
        return html
    
    def _generate_cycle_time_section(self, report: ReportData) -> str:
        """Generate cycle time section with clickable issue keys."""
        if not report.cycle_time_data:
            return ""
        
        html = f"<h2>{self._['cycle_time']}</h2>"
        html += "<div class='table-responsive'><table><thead><tr>"
        for header in [self._["issue_key"], self._["project_key"], self._["issue_type"],
                      self._["assignee"], self._["reporter"], self._["start_progress_date"],
                      self._["done_date"], self._["cycle_time_days"], self._["cycle_time_hours"],
                      self._["reopened_flag"]]:
            html += f"<th>{header}</th>"
        html += "</tr></thead><tbody>"
        
        for ct in report.cycle_time_data:
            html += "<tr>"
            html += f"<td><a href='{self.jira_base}/browse/{ct.issue_key}' target='_blank'>{ct.issue_key}</a></td>"
            html += f"<td><a href='{self.jira_base}/projects/{ct.project_key}' target='_blank'>{ct.project_key}</a></td>"
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
    
    def _generate_aging_wip_section(self, report: ReportData) -> str:
        """Generate aging WIP section with clickable issue keys."""
        if not report.aging_wip_data:
            return ""
        
        html = f"<h2>{self._['aging_wip']}</h2>"
        html += "<div class='table-responsive'><table><thead><tr>"
        for header in [self._["issue_key"], self._["project_key"], self._["status"],
                      self._["assignee"], self._["created"], self._["last_status_change"],
                      self._["aging_days"], self._["blocked_flag"], self._["due_date"],
                      self._["overdue_flag"]]:
            html += f"<th>{header}</th>"
        html += "</tr></thead><tbody>"
        
        for aw in report.aging_wip_data:
            html += "<tr>"
            html += f"<td><a href='{self.jira_base}/browse/{aw.issue_key}' target='_blank'>{aw.issue_key}</a></td>"
            html += f"<td><a href='{self.jira_base}/projects/{aw.project_key}' target='_blank'>{aw.project_key}</a></td>"
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
    
    def _generate_overdue_section(self, report: ReportData) -> str:
        """Generate overdue section with clickable issue keys."""
        if not report.overdue_data:
            return ""
        
        html = f"<h2>{self._['overdue']}</h2>"
        html += "<div class='table-responsive'><table><thead><tr>"
        for header in [self._["issue_key"], self._["project_key"], self._["assignee"],
                      self._["status"], self._["due_date"], self._["days_overdue"],
                      self._["priority"]]:
            html += f"<th>{header}</th>"
        html += "</tr></thead><tbody>"
        
        for od in report.overdue_data:
            html += "<tr>"
            html += f"<td><a href='{self.jira_base}/browse/{od.issue_key}' target='_blank'>{od.issue_key}</a></td>"
            html += f"<td><a href='{self.jira_base}/projects/{od.project_key}' target='_blank'>{od.project_key}</a></td>"
            html += f"<td>{od.assignee or ''}</td>"
            html += f"<td>{od.status}</td>"
            html += f"<td>{od.due_date.strftime('%Y-%m-%d') if od.due_date else ''}</td>"
            html += f"<td>{od.days_overdue}</td>"
            html += f"<td>{od.priority or ''}</td>"
            html += "</tr>"
        
        html += "</tbody></table></div>"
        return html
    
    def _generate_reopened_section(self, report: ReportData) -> str:
        """Generate reopened section with clickable issue keys."""
        if not report.reopened_data:
            return ""
        
        html = f"<h2>{self._['reopened']}</h2>"
        html += "<div class='table-responsive'><table><thead><tr>"
        for header in [self._["issue_key"], self._["project_key"], self._["assignee"],
                      self._["done_date"], self._["reopen_date"], self._["reopen_count"],
                      self._["current_status"]]:
            html += f"<th>{header}</th>"
        html += "</tr></thead><tbody>"
        
        for rd in report.reopened_data:
            html += "<tr>"
            html += f"<td><a href='{self.jira_base}/browse/{rd.issue_key}' target='_blank'>{rd.issue_key}</a></td>"
            html += f"<td><a href='{self.jira_base}/projects/{rd.project_key}' target='_blank'>{rd.project_key}</a></td>"
            html += f"<td>{rd.assignee or ''}</td>"
            html += f"<td>{rd.done_date.strftime('%Y-%m-%d') if rd.done_date else ''}</td>"
            html += f"<td>{rd.reopen_date.strftime('%Y-%m-%d') if rd.reopen_date else ''}</td>"
            html += f"<td>{rd.reopen_count}</td>"
            html += f"<td>{rd.current_status}</td>"
            html += "</tr>"
        
        html += "</tbody></table></div>"
        return html
    
    def _generate_charts_section(self, report: ReportData) -> str:
        """Generate charts section with Chart.js interactive charts."""
        html = f"<h2>{self._['charts']}</h2>"
        
        # Prepare data for Chart.js charts
        chart_data = self._prepare_chart_data(report)
        
        # 1. Closed tasks by week - Chart.js
        if chart_data.get('closed_by_week'):
            html += f"<h3>{self._['closed_by_week']}</h3>"
            html += f'<div class="chart-container"><canvas id="chart-closed-week"></canvas></div>'
            html += f'<script>const closedWeekData = {chart_data["closed_by_week"]};</script>'
        
        # 2. Worklog by employee - Chart.js (horizontal bars for readability)
        if chart_data.get('worklog_by_employee'):
            html += f"<h3>{self._['worklog_by_employee']}</h3>"
            html += f'<div class="chart-container"><canvas id="chart-worklog-employee"></canvas></div>'
            html += f'<script>const worklogEmployeeData = {chart_data["worklog_by_employee"]};</script>'
        
        # 3. Aging buckets - Chart.js
        if chart_data.get('aging_buckets'):
            html += f"<h3>{self._['aging_buckets']}</h3>"
            html += f'<div class="chart-container"><canvas id="chart-aging-buckets"></canvas></div>'
            html += f'<script>const agingBucketsData = {chart_data["aging_buckets"]};</script>'
        
        # 4. Reopened by project - Chart.js
        if chart_data.get('reopened_by_project'):
            html += f"<h3>{self._['reopened_by_project']}</h3>"
            html += f'<div class="chart-container"><canvas id="chart-reopened-project"></canvas></div>'
            html += f'<script>const reopenedProjectData = {chart_data["reopened_by_project"]};</script>'
        
        # 5. Cycle time by week - Chart.js
        if chart_data.get('cycle_time_by_week'):
            html += f"<h3>{self._['cycle_time_by_week']}</h3>"
            html += f'<div class="chart-container"><canvas id="chart-cycle-time-week"></canvas></div>'
            html += f'<script>const cycleTimeWeekData = {chart_data["cycle_time_by_week"]};</script>'
        
        # 6. Status by project - Chart.js
        if chart_data.get('status_by_project'):
            html += f"<h3>{self._['status_by_project']}</h3>"
            html += f'<div class="chart-container"><canvas id="chart-status-project"></canvas></div>'
            html += f'<script>const statusProjectData = {chart_data["status_by_project"]};</script>'
        
        # Add Chart.js initialization script
        html += """
        <script>
        // Chart.js configuration for all charts
        Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
        Chart.defaults.color = '#333';
        
        // 1. Closed tasks by week
        if (typeof closedWeekData !== 'undefined') {
            new Chart(document.getElementById('chart-closed-week'), {
                type: 'bar',
                data: closedWeekData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'top' },
                        tooltip: { mode: 'index', intersect: false }
                    },
                    scales: {
                        x: { stacked: true },
                        y: { stacked: true, beginAtZero: true }
                    }
                }
            });
        }
        
        // 2. Worklog by employee (horizontal bars for readability)
        if (typeof worklogEmployeeData !== 'undefined') {
            new Chart(document.getElementById('chart-worklog-employee'), {
                type: 'bar',
                data: worklogEmployeeData,
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: { enabled: true }
                    },
                    scales: {
                        x: { beginAtZero: true, title: { display: true, text: 'Hours' } },
                        y: { ticks: { autoSkip: false } }
                    }
                }
            });
        }
        
        // 3. Aging buckets
        if (typeof agingBucketsData !== 'undefined') {
            new Chart(document.getElementById('chart-aging-buckets'), {
                type: 'bar',
                data: agingBucketsData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: { enabled: true }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }
        
        // 4. Reopened by project
        if (typeof reopenedProjectData !== 'undefined') {
            new Chart(document.getElementById('chart-reopened-project'), {
                type: 'bar',
                data: reopenedProjectData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: { enabled: true }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }
        
        // 5. Cycle time by week
        if (typeof cycleTimeWeekData !== 'undefined') {
            new Chart(document.getElementById('chart-cycle-time-week'), {
                type: 'line',
                data: cycleTimeWeekData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'top' },
                        tooltip: { mode: 'index', intersect: false }
                    },
                    scales: {
                        y: { beginAtZero: true, title: { display: true, text: 'Days' } }
                    }
                }
            });
        }
        
        // 6. Status by project
        if (typeof statusProjectData !== 'undefined') {
            new Chart(document.getElementById('chart-status-project'), {
                type: 'bar',
                data: statusProjectData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'top' },
                        tooltip: { mode: 'index', intersect: false }
                    },
                    scales: {
                        x: { stacked: true },
                        y: { stacked: true, beginAtZero: true }
                    }
                }
            });
        }
        
        // Download report as static HTML file
        function downloadReport() {
            // Get the HTML content
            const htmlContent = document.documentElement.outerHTML;
            
            // Create a Blob with the HTML content
            const blob = new Blob([htmlContent], { type: 'text/html' });
            
            // Create download link
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // Generate filename with date
            const now = new Date();
            const dateStr = now.toISOString().split('T')[0];
            a.download = `jira_report_${dateStr}.html`;
            
            // Trigger download
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
        
        // Auto-download when page loads (for new tab reports)
        window.addEventListener('load', function() {
            // Check if this is a new tab report (not the main app)
            if (window.opener || window.location.search.includes('autodownload')) {
                setTimeout(function() {
                    downloadReport();
                }, 1000); // Delay to ensure charts are rendered
            }
        });

    </script>
        """
        
        return html
    
    def _prepare_chart_data(self, report: ReportData) -> Dict:
        """Prepare data for Chart.js charts."""
        import json
        
        chart_data = {}
        
        # 1. Closed tasks by week
        if report.weekly_throughput:
            weekly_data = defaultdict(lambda: defaultdict(int))
            for wt in report.weekly_throughput:
                week_label = wt.week_start.strftime('%Y-%m-%d')
                weekly_data[wt.project_key][week_label] = wt.closed_tasks_count
            
            projects = sorted(set(wt.project_key for wt in report.weekly_throughput))
            weeks = sorted(set(wt.week_start.strftime('%Y-%m-%d') for wt in report.weekly_throughput))
            
            datasets = []
            colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b']
            for i, proj in enumerate(projects):
                values = [weekly_data[proj].get(week, 0) for week in weeks]
                datasets.append({
                    'label': proj,
                    'data': values,
                    'backgroundColor': colors[i % len(colors)]
                })
            
            chart_data['closed_by_week'] = json.dumps({
                'labels': weeks,
                'datasets': datasets
            })
        
        # 2. Worklog by employee (horizontal bars)
        if report.employee_metrics:
            employees = [emp.display_name for emp in report.employee_metrics]
            hours = [emp.worklog_hours for emp in report.employee_metrics]
            
            chart_data['worklog_by_employee'] = json.dumps({
                'labels': employees,
                'datasets': [{
                    'label': 'Hours',
                    'data': hours,
                    'backgroundColor': '#3498db'
                }]
            })
        
        # 3. Aging buckets
        buckets = {"0-7": 0, "8-14": 0, "15-30": 0, "30+": 0}
        if report.aging_wip_data:
            for aw in report.aging_wip_data:
                if aw.aging_days <= 7:
                    buckets["0-7"] += 1
                elif aw.aging_days <= 14:
                    buckets["8-14"] += 1
                elif aw.aging_days <= 30:
                    buckets["15-30"] += 1
                else:
                    buckets["30+"] += 1
            
            chart_data['aging_buckets'] = json.dumps({
                'labels': list(buckets.keys()),
                'datasets': [{
                    'label': 'Count',
                    'data': list(buckets.values()),
                    'backgroundColor': '#f39c12'
                }]
            })
        
        # 4. Reopened by project
        if report.project_metrics:
            projects = [proj.project_key for proj in report.project_metrics]
            reopened = [proj.reopened_tasks for proj in report.project_metrics]
            
            chart_data['reopened_by_project'] = json.dumps({
                'labels': projects,
                'datasets': [{
                    'label': 'Reopened Count',
                    'data': reopened,
                    'backgroundColor': '#e74c3c'
                }]
            })
        
        # 5. Cycle time by week
        if report.weekly_cycle_time:
            week_labels = sorted(set(
                wt.week_start.strftime('%Y-%m-%d') 
                for wt in report.weekly_cycle_time
            ))
            projects = sorted(set(wt.project_key for wt in report.weekly_cycle_time))
            
            datasets = []
            colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b']
            for i, proj in enumerate(projects):
                values = []
                for week in week_labels:
                    ct = next(
                        (wt for wt in report.weekly_cycle_time 
                            if wt.week_start.strftime('%Y-%m-%d') == week and wt.project_key == proj
                        ), None)
                    values.append(ct.median_cycle_time if ct and ct.median_cycle_time else None)
                
                # Filter out None values
                filtered_values = [v for v in values if v is not None]
                if filtered_values:
                    datasets.append({
                        'label': proj,
                        'data': values,
                        'borderColor': colors[i % len(colors)],
                        'fill': False,
                        'tension': 0.1
                    })
            
            chart_data['cycle_time_by_week'] = json.dumps({
                'labels': week_labels,
                'datasets': datasets
            })
        
        # 6. Status by project
        if report.status_distribution:
            all_statuses = sorted(set(sd.status for sd in report.status_distribution))
            all_projects = sorted(set(sd.project_key for sd in report.status_distribution))
            
            data = defaultdict(lambda: defaultdict(int))
            for sd in report.status_distribution:
                data[sd.project_key][sd.status] = sd.count
            
            datasets = []
            colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b', '#1abc9c']
            for i, status in enumerate(all_statuses):
                values = [data[proj].get(status, 0) for proj in all_projects]
                datasets.append({
                    'label': status,
                    'data': values,
                    'backgroundColor': colors[i % len(colors)]
                })
            
            chart_data['status_by_project'] = json.dumps({
                'labels': all_projects,
                'datasets': datasets
            })
        
        return chart_data
    
    def _generate_raw_data_sections(self, report: ReportData) -> str:
        """Generate raw data sections with responsive wrappers and clickable issue keys."""
        html = ""
        
        # Raw Issues
        if report.raw_issues:
            html += f"<h2>{self._['raw_issues']}</h2>"
            html += "<div class='table-responsive'><table><thead><tr>"
            for header in [self._["issue_key"], self._["project_key"], self._["issue_type"],
                          self._["summary"], self._["status"], self._["created"],
                          self._["assignee"], self._["reporter"], self._["due_date"],
                          self._["priority"], self._["cycle_time_days"], self._["reopened_flag"],
                          self._["blocked_flag"], self._["overdue_flag"], self._["aging_days"]]:
                html += f"<th>{header}</th>"
            html += "</tr></thead><tbody>"
            
            for issue in report.raw_issues:
                html += "<tr>"
                html += f"<td><a href='{self.jira_base}/browse/{issue.issue_key}' target='_blank'>{issue.issue_key}</a></td>"
                html += f"<td><a href='{self.jira_base}/projects/{issue.project_key}' target='_blank'>{issue.project_key}</a></td>"
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
            html += f"<h2>{self._['raw_worklogs']}</h2>"
            html += "<div class='table-responsive'><table><thead><tr>"
            for header in [self._["issue_key"], self._["project_key"], self._["employee_name"],
                          self._["started"], self._["time_spent_hours"], self._["comment"]]:
                html += f"<th>{header}</th>"
            html += "</tr></thead><tbody>"
            
            for wl in report.raw_worklogs:
                html += "<tr>"
                html += f"<td><a href='{self.jira_base}/browse/{wl.issue_key}' target='_blank'>{wl.issue_key}</a></td>"
                html += f"<td><a href='{self.jira_base}/projects/{wl.project_key}' target='_blank'>{wl.project_key}</a></td>"
                html += f"<td>{wl.display_name}</td>"
                html += f"<td>{wl.started.strftime('%Y-%m-%d %H:%M') if wl.started else ''}</td>"
                html += f"<td>{wl.time_spent_hours:.2f}</td>"
                html += f"<td>{wl.comment or ''}</td>"
                html += "</tr>"
            
            html += "</tbody></table></div>"
        
        # Raw Transitions
        if report.raw_transitions:
            html += f"<h2>{self._['raw_transitions']}</h2>"
            html += "<div class='table-responsive'><table><thead><tr>"
            for header in [self._["issue_key"], self._["project_key"], self._["from_status"],
                          self._["to_status"], self._["transition_date"], self._["transition_author"]]:
                html += f"<th>{header}</th>"
            html += "</tr></thead><tbody>"
            
            for trans in report.raw_transitions:
                html += "<tr>"
                html += f"<td><a href='{self.jira_base}/browse/{trans.issue_key}' target='_blank'>{trans.issue_key}</a></td>"
                html += f"<td><a href='{self.jira_base}/projects/{trans.project_key}' target='_blank'>{trans.project_key}</a></td>"
                html += f"<td>{trans.from_status}</td>"
                html += f"<td>{trans.to_status}</td>"
                html += f"<td>{trans.transition_date.strftime('%Y-%m-%d %H:%M') if trans.transition_date else ''}</td>"
                html += f"<td>{trans.transition_author or ''}</td>"
                html += "</tr>"
            
            html += "</tbody></table></div>"
        
        return html



    def _generate_employee_worklog_summary_section(self, report: ReportData) -> str:
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
        
        html = f"<h2>{self._get('worklog_by_employee', 'Worklog by Employee')}</h2>"
        html += "<div class='table-responsive'><table><thead><tr>"
        for header in [self._get('employee_name', 'Employee Name'), 
                      self._get('worklog_hours', 'Worklog Hours'),
                      self._get('project_key', 'Projects Count')]:
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
        html += f"<td>{self._get('total', 'TOTAL')}</td>"
        html += f"<td>{sum(e['total_hours'] for e in sorted_employees):.2f}</td>"
        html += f"<td>{len(employee_totals)}</td>"
        html += "</tr>"
        
        html += "</tbody></table></div>"
        return html
    
    def _get(self, key, default=None):
        """Safe get from localization dict."""
        return self._.get(key, default) if hasattr(self, '_') else default


# Localization strings
LOCALIZATION = {
    "en": {
        "summary": "Summary",
        "by_employee": "By Employee",
        "by_project": "By Project",
        "weekly_throughput": "Weekly Throughput",
        "cycle_time": "Cycle Time",
        "aging_wip": "Aging WIP",
        "overdue": "Overdue",
        "reopened": "Reopened",
        "raw_issues": "Raw Issues",
        "raw_worklogs": "Raw Worklogs",
        "raw_transitions": "Raw Transitions",
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
        "issue_key": "Issue Key",
        "summary": "Summary",
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
        "median_cycle_time": "Median Cycle Time",
        "overdue_count": "Overdue Count",
        "project": "Project",
        "throughput_count": "Throughput",
        "wip_count": "WIP Count",
        "aging_7": "Aging >7 days",
        "aging_14": "Aging >14 days",
        "aging_30": "Aging >30 days",
        "blocked_count": "Blocked Count",
        "week_start": "Week Start",
        "week_end": "Week End",
        "created_count": "Created Count",
        "closed_count": "Closed Count",
        "net_flow": "Net Flow",
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
        "from_status": "From Status",
        "to_status": "To Status",
        "transition_date": "Transition Date",
        "transition_author": "Transition Author",
        "started": "Started",
        "time_spent_hours": "Time Spent (hours)",
        "comment": "Comment",
        "total": "TOTAL",
        "cycle_time_by_week": "Cycle Time by Week",
        "status_by_project": "Status by Project",
        "charts": "Charts",
        "closed_by_week": "Closed Tasks by Week",
        "cycle_time_by_week": "Cycle Time by Week",
        "worklog_by_employee": "Worklog by Employee",
        "aging_buckets": "Aging WIP Buckets",
        "status_by_project": "Status by Project",
        "reopened_by_project": "Reopened by Project",
    },
    "ru": {
        "summary": "Сводка",
        "by_employee": "По сотрудникам",
        "by_project": "По проектам",
        "weekly_throughput": "Недельный Throughput",
        "cycle_time": "Cycle Time",
        "aging_wip": "Aging WIP",
        "overdue": "Просроченные",
        "reopened": "Переоткрытые",
        "raw_issues": "Сырые данные задач",
        "raw_worklogs": "Сырые данные трудозатрат",
        "raw_transitions": "Сырые данные переходов",
        "metric": "Показатель",
        "value": "Значение",
        "report_period": "Период отчета",
        "total_worklog_hours": "Всего часов трудозатрат",
        "total_created_issues": "Всего создано задач",
        "total_closed_issues": "Всего закрыто задач",
        "throughput": "Throughput",
        "median_cycle_time": "Медиана Cycle Time (дни)",
        "p85_cycle_time": "85-й перцентиль Cycle Time (дни)",
        "overdue_tasks": "Просроченные задачи",
        "reopened_tasks": "Переоткрытые задачи",
        "blocked_tasks": "Заблокированные задачи",
        "top_oldest_issues": "Топ-5 самых старых открытых задач",
        "issue_key": "Ключ задачи",
        "summary": "Название",
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
        "avg_cycle_time": "Средний Cycle Time",
        "median_cycle_time": "Медиана Cycle Time",
        "overdue_count": "Просрочено",
        "project": "Проект",
        "throughput_count": "Throughput",
        "wip_count": "WIP",
        "aging_7": "Возраст >7 дней",
        "aging_14": "Возраст >14 дней",
        "aging_30": "Возраст >30 дней",
        "blocked_count": "Заблокировано",
        "week_start": "Начало недели",
        "week_end": "Конец недели",
        "created_count": "Создано",
        "closed_count": "Закрыто",
        "net_flow": "Чистый поток",
        "issue_type": "Тип задачи",
        "reporter": "Репортер",
        "start_progress_date": "Дата начала работы",
        "done_date": "Дата завершения",
        "cycle_time_days": "Cycle Time (дни)",
        "cycle_time_hours": "Cycle Time (часы)",
        "reopened_flag": "Переоткрыта?",
        "last_status_change": "Последний переход",
        "blocked_flag": "Заблокирована?",
        "due_date": "Срок",
        "overdue_flag": "Просрочена?",
        "priority": "Приоритет",
        "days_overdue": "Дней просрочки",
        "reopen_date": "Дата переоткрытия",
        "current_status": "Текущий статус",
        "from_status": "Из статуса",
        "to_status": "В статус",
        "transition_date": "Дата перехода",
        "transition_author": "Автор перехода",
        "started": "Начало",
        "time_spent_hours": "Часы",
        "comment": "Комментарий",
        "total": "ИТОГО",
        "cycle_time_by_week": "Cycle Time по неделям",
        "status_by_project": "Статусы по проектам",
        "charts": "Графики",
        "closed_by_week": "Закрытые задачи по неделям",
        "cycle_time_by_week": "Cycle Time по неделям",
        "worklog_by_employee": "Трудозатраты по сотрудникам",
        "aging_buckets": "Возрастные группы WIP",
        "status_by_project": "Статусы по проектам",
        "reopened_by_project": "Переоткрытые по проектам",
    }
}
