#!/usr/bin/env python3
"""Test script to debug HTML export issues."""
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    logger.info("Importing modules...")
    from app.models.schemas import (
        ReportData, EmployeeMetrics, ProjectMetrics, 
        IssueData, WorklogEntry, IssueTransition,
        WeeklyThroughput, WeeklyCycleTime, CycleTimeData, AgingWipData,
    )
    from app.services.html_exporter import HtmlExporter
    logger.info("Modules imported successfully")
    
    # Create minimal test data
    logger.info("Creating test data...")
    report = ReportData(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        total_worklog_hours=0,
        total_created_issues=0,
        total_closed_issues=0,
        throughput=0,
        median_cycle_time=None,
        p85_cycle_time=None,
        overdue_tasks_count=0,
        reopened_tasks_count=0,
        blocked_tasks_count=0,
        employee_metrics=[],
        project_metrics=[],
        weekly_throughput=[],
        weekly_cycle_time=[],
        cycle_time_data=[],
        aging_wip_data=[],
        overdue_data=[],
        reopened_data=[],
        include_raw_data=False
    )
    logger.info("Test data created successfully")
    
    # Try to create HtmlExporter
    logger.info("Creating HtmlExporter...")
    exporter = HtmlExporter()
    logger.info("HtmlExporter created successfully")
    
    # Try to generate HTML
    logger.info("Generating HTML report...")
    html = exporter.generate(report)
    logger.info(f"HTML report generated successfully! Length: {len(html)} characters")
    
except Exception as e:
    logger.error(f"Error: {type(e).__name__}: {e}", exc_info=True)
    sys.exit(1)
