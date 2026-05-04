import logging
from typing import List, Optional, Dict
from datetime import datetime
from io import BytesIO
from collections import defaultdict
import base64

from app.models.schemas import (
    ReportData, EmployeeMetrics, ProjectMetrics, 
    IssueData, WorklogEntry, IssueTransition,
    WeeklyThroughput, WeeklyCycleTime, CycleTimeData, AgingWipData,
    OverdueData, ReopenedData, StatusDistribution
)
from app.models.config import settings

logger = logging.getLogger(__name__)


class HtmlExporter:
    """Generates HTML reports with embedded charts."""
    
    def __init__(self, lang: str = None):
        self.lang = lang or settings.REPORT_LANG
        if self.lang not in LOCALIZATION:
            self.lang = "en"
        self._ = LOCALIZATION[self.lang]
        self.jira_base = settings.JIRA_BASE_URL.rstrip('/')
        
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
            closed_jql = f"project in ({project_keys}) AND status in ({",".join([f'"{s}"' for s in settings.done_statuses_list])}) AND status changed to Done during ('{start_str}', '{end_str}')"
            overdue_jql = f"project in ({project_keys}) AND duedate < now() AND status not in ({",".join([f'"{s}"' for s in settings.done_statuses_list])})"
            reopened_jql = f"project in ({project_keys}) AND status changed from Done to * during ('{start_str}', '{end_str}')"
            blocked_jql = f"project in ({project_keys}) AND status in ({",".join([f'"{s}"' for s in settings.blocked_statuses_list])})"
            
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
                    c.style.opacity = '0';
                });
                
                // Add active class to clicked button and corresponding content
                button.classList.add('active');
                const tabId = button.getAttribute('data-tab');
                const targetContent = document.getElementById(tabId);
                targetContent.classList.add('active');
                setTimeout(function() {
                    targetContent.style.opacity = '1';
                }, 50);
            });
        });
        
        // Summary navigation links
        document.querySelectorAll('.summary-nav-link').forEach(function(link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const tabId = link.getAttribute('data-tab');
                if (tabId) {
                    // Find and click the corresponding tab button
                    document.querySelectorAll('.tab-button').forEach(function(b) {
                        if (b.getAttribute('data-tab') === tabId) {
                            b.click();
                        }
                    });
                }
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
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #3498db;
            transition: transform 0.2s;
            cursor: pointer;
        }
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
            border-left-color: #e74c3c;
        }
            border-left-color: #f39c12;
        }
            border-left-color: #3498db;
        }
            font-size: 36px;
            font-weight: bold;
            color: #2c3e50;
        }
            color: #7f8c8d;
            font-size: 14px;
            margin-top: 5px;
        }
            background: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid #f39c12;
        }
            border-left-color: #e74c3c;
        }
            border-left-color: #f39c12;
        }
            border-left-color: #3498db;
        }
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }
            color: #555;
            font-size: 14px;
            margin-bottom: 5px;
        }
            color: #7f8c8d;
            font-size: 12px;
        }
        .no-data {
            color: #7f8c8d;
            font-style: italic;
            padding: 20px;
            text-align: center;
        }
        
        /* Summary Navigation Block */
        .summary-nav {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 30px;
            color: white;
        }
        .summary-nav h2 {
            color: white;
            border-bottom: 2px solid rgba(255,255,255,0.3);
            margin-top: 0;
        }
        .summary-nav-links {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }
        .summary-nav-link {
            padding: 8px 16px;
            background: rgba(255,255,255,0.2);
            border: 1px solid rgba(255,255,255,0.3);
            border-radius: 6px;
            color: white;
            text-decoration: none;
            font-size: 14px;
            transition: all 0.3s;
            cursor: pointer;
        }
        .summary-nav-link:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-1px);
            color: white;
            text-decoration: none;
        }
        
            width: 100%;
            max-width: 500px;
            height: 300px;
            margin: 20px auto;
            position: relative;
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }
"""
    
    def _generate_jira_link(self, jql: str, text: str) -> str:
        """Generate a JIRA filter link."""
        return f'<a href="{self.jira_base}/issues/?jql={jql}" target="_blank">{text}</a>'
    
    def _generate_summary_section(self, report: ReportData, created_jql: str, closed_jql: str, 
                                   overdue_jql: str, reopened_jql: str, blocked_jql: str) -> str:
        """Generate summary section with JIRA links and navigation."""
        html = f"<h2>{self._['summary']}</h2>"
        
        # Add summary navigation block
        html += '<div class="summary-nav">'
        html += f'<h2>{self._["summary"]}</h2>'
        html += '<div class="summary-nav-links">'
        html += f'<a class="summary-nav-link" data-tab="by-employee">{self._["by_employee"]}</a>'
        html += f'<a class="summary-nav-link" data-tab="by-project">{self._["by_project"]}</a>'
        html += f'<a class="summary-nav-link" data-tab="charts">{self._["charts"]}</a>'
        html += f'<a class="summary-nav-link" data-tab="raw-data">{self._["raw_issues"]}</a>'
        html += '</div></div>'
        
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
    