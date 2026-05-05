"""
HTML Exporter module for Jira Report application.

This module generates HTML reports with embedded charts.
Refactored from original 1400 lines to use modular components.
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime
from urllib.parse import quote

from app.models.schemas import ReportData
from app.models.config import get_settings
from app.services.localization import get_localization, LOCALIZATION
from app.services.html_styles import get_css
from app.services.html_sections import (
    generate_summary_section,
    generate_by_employee_section,
    generate_by_project_section,
    generate_weekly_throughput_section,
    generate_cycle_time_section,
    generate_aging_wip_section,
    generate_overdue_section,
    generate_reopened_section,
    generate_employee_worklog_summary_section,
    generate_raw_data_sections,
)
from app.services.html_charts import generate_charts_section


logger = logging.getLogger(__name__)


class HtmlExporter:
    """Generates HTML reports with embedded charts."""
    
    def __init__(self, lang: str = None):
        self.settings = get_settings()
        self.lang = lang or self.settings.REPORT_LANG
        if self.lang not in LOCALIZATION:
            self.lang = "en"
        self._ = get_localization(self.lang)
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
            
            # URL-encode JQL queries for use in links
            created_jql_encoded = quote(created_jql)
            closed_jql_encoded = quote(closed_jql)
            overdue_jql_encoded = quote(overdue_jql)
            reopened_jql_encoded = quote(reopened_jql)
            blocked_jql_encoded = quote(blocked_jql)
            
            logger.debug("Building HTML structure")
            html_parts = []
            
            # HTML header with localized strings
            logger.debug("Adding HTML header")
            interval_str = f"{report.start_date.strftime('%Y-%m-%d')} - {report.end_date.strftime('%Y-%m-%d')}"
            report_title = self._["report_title"]
            report_header = self._["report_header"]
            download_text = self._["download_report"]
            
            html_parts.append(f"""<!DOCTYPE html>
<html lang="{self.lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title} {interval_str}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
""")
            
            # CSS
            logger.debug("Generating CSS")
            html_parts.append(get_css())
            html_parts.append(f"""    </style>
</head>
<body>
    <div class="container">
        <h1>📊 {report_header}</h1>
        <p class="subtitle">{interval_str}</p>
        <button id="downloadBtn" class="download-btn" onclick="downloadReport()">📥 {download_text}</button>
""")
            
            # Summary section
            logger.debug("Generating summary section")
            html_parts.append(generate_summary_section(
                report, self.jira_base, self._,
                created_jql, closed_jql, overdue_jql, reopened_jql, blocked_jql,
                created_jql_encoded, closed_jql_encoded, overdue_jql_encoded, reopened_jql_encoded, blocked_jql_encoded
            ))
            
            # Tab navigation with localized strings
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
            
            # Tab contents
            logger.debug("Generating by-employee section")
            html_parts.append("""        <div id="by-employee" class="tab-content active">""")
            html_parts.append(generate_by_employee_section(report, self.jira_base, self._))
            html_parts.append("""        </div>""")
            
            # Employee worklog summary section
            logger.debug("Generating employee worklog summary section")
            html_parts.append("""        <div id="employee-worklog-summary" class="tab-content">""")
            html_parts.append(generate_employee_worklog_summary_section(report, self._))
            html_parts.append("""        </div>""")
            
            # By project section
            logger.debug("Generating by-project section")
            html_parts.append("""        <div id="by-project" class="tab-content">""")
            html_parts.append(generate_by_project_section(report, self.jira_base, self._))
            html_parts.append("""        </div>""")
            
            # Weekly throughput section
            logger.debug("Generating weekly-throughput section")
            html_parts.append("""        <div id="weekly-data" class="tab-content">""")
            html_parts.append(generate_weekly_throughput_section(report, self.jira_base, self._))
            html_parts.append("""        </div>""")
            
            # Cycle time section
            logger.debug("Generating cycle-time section")
            html_parts.append("""        <div id="cycle-time" class="tab-content">""")
            html_parts.append(generate_cycle_time_section(report, self.jira_base, self._))
            html_parts.append("""        </div>""")
            
            # Aging WIP section
            logger.debug("Generating aging-wip section")
            html_parts.append("""        <div id="aging-wip" class="tab-content">""")
            html_parts.append(generate_aging_wip_section(report, self.jira_base, self._))
            html_parts.append("""        </div>""")
            
            # Overdue section
            logger.debug("Generating overdue section")
            html_parts.append("""        <div id="overdue" class="tab-content">""")
            html_parts.append(generate_overdue_section(report, self.jira_base, self._))
            html_parts.append("""        </div>""")
            
            # Reopened section
            logger.debug("Generating reopened section")
            html_parts.append("""        <div id="reopened" class="tab-content">""")
            html_parts.append(generate_reopened_section(report, self.jira_base, self._))
            html_parts.append("""        </div>""")
            
            # Charts section
            logger.debug("Generating charts section")
            html_parts.append("""        <div id="charts" class="tab-content">""")
            html_parts.append(generate_charts_section(report, self._))
            html_parts.append("""        </div>""")
            
            # Raw data section
            logger.debug("Generating raw-data section")
            html_parts.append("""        <div id="raw-data" class="tab-content">""")
            if report.include_raw_data:
                html_parts.append(generate_raw_data_sections(report, self.jira_base, self._))
            html_parts.append("""        </div>""")
            
            # JavaScript for tab navigation
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
    
    def _generate_jira_link(self, jql: str, text: str) -> str:
        """Generate a JIRA filter link."""
        encoded_jql = quote(jql, safe='')
        return f'<a href="{self.jira_base}/issues/?jql={encoded_jql}" target="_blank">{text}</a>'
    
    def _get(self, key: str, default=None):
        """Safe get from localization dict."""
        return self._.get(key, default) if hasattr(self, '_') else default
