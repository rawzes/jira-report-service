"""
HTML Charts module for Jira Report application.

This module contains methods for generating Chart.js charts in the HTML report.
"""

import json
from typing import Dict
from collections import defaultdict

from app.models.schemas import ReportData


def generate_charts_section(report: ReportData, _: Dict) -> str:
    """Generate charts section with Chart.js interactive charts."""
    html = f"<h2>{_['charts']}</h2>"
    
    # Prepare data for Chart.js charts
    chart_data = _prepare_chart_data(report)
    
    # 1. Closed tasks by week - Chart.js
    if chart_data.get('closed_by_week'):
        html += f"<h3>{_['closed_by_week']}</h3>"
        html += f'<div class="chart-container"><canvas id="chart-closed-week"></canvas></div>'
        html += f'<script>const closedWeekData = {chart_data["closed_by_week"]};</script>'
    
    # 2. Worklog by employee - Chart.js (horizontal bars for readability)
    if chart_data.get('worklog_by_employee'):
        html += f"<h3>{_['worklog_by_employee']}</h3>"
        html += f'<div class="chart-container"><canvas id="chart-worklog-employee"></canvas></div>'
        html += f'<script>const worklogEmployeeData = {chart_data["worklog_by_employee"]};</script>'
    
    # 3. Aging buckets - Chart.js
    if chart_data.get('aging_buckets'):
        html += f"<h3>{_['aging_buckets']}</h3>"
        html += f'<div class="chart-container"><canvas id="chart-aging-buckets"></canvas></div>'
        html += f'<script>const agingBucketsData = {chart_data["aging_buckets"]};</script>'
    
    # 4. Reopened by project - Chart.js
    if chart_data.get('reopened_by_project'):
        html += f"<h3>{_['reopened_by_project']}</h3>"
        html += f'<div class="chart-container"><canvas id="chart-reopened-project"></canvas></div>'
        html += f'<script>const reopenedProjectData = {chart_data["reopened_by_project"]};</script>'
    
    # 5. Cycle time by week - Chart.js
    if chart_data.get('cycle_time_by_week'):
        html += f"<h3>{_['cycle_time_by_week']}</h3>"
        html += f'<div class="chart-container"><canvas id="chart-cycle-time-week"></canvas></div>'
        html += f'<script>const cycleTimeWeekData = {chart_data["cycle_time_by_week"]};</script>'
    
    # 6. Status by project - Chart.js
    if chart_data.get('status_by_project'):
        html += f"<h3>{_['status_by_project']}</h3>"
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


def _prepare_chart_data(report: ReportData) -> Dict:
    """Prepare data for Chart.js charts."""
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
