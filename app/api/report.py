import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from typing import Optional, List
from datetime import date, timedelta
import io
import json
from urllib.parse import urlencode

from app.models.schemas import MonthlyReportRequest, CustomReportRequest, ReportData
from app.models.config import get_settings
from app.services.jira_client import JiraClient
from app.services.report_builder import ReportBuilder
from app.services.html_exporter import HtmlExporter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/monthly")
async def generate_monthly_report_get(
    year: int,
    month: int,
    project_keys: Optional[str] = None,
    group: Optional[str] = Query(None, description="User group for report"),
    lang: str = Query("ru", description="Language for report (en, ru)"),
    format: str = Query("html", description="Response format: html, htmldownload or json")
):
    """
    Generate monthly Jira report (GET endpoint).
    
    Args:
        year: Report year
        month: Report month (1-12)
        project_keys: Comma-separated project keys (e.g., "PROJ1,PROJ2")
        group: User group for report (e.g., "IT")
        lang: Language for report (en, ru)
        format: Response format (html, htmldownload or json)
    
    Returns:
        HTMLResponse or JSONResponse with report data
    """
    # Parse project_keys from comma-separated string to list
    parsed_project_keys = None
    if project_keys:
        parsed_project_keys = [k.strip() for k in project_keys.split(",") if k.strip()]
    
    # Create request object with hardcoded group_by_projects=True and include_raw_data=True
    request = MonthlyReportRequest(
        year=year,
        month=month,
        project_keys=parsed_project_keys,
        group=group,
        group_by_projects=True,
        include_raw_data=True
    )
    
    return await _generate_report(request, lang, format)


@router.post("/monthly")
async def generate_monthly_report_post(
    request: MonthlyReportRequest,
    lang: str = "ru",
    format: str = Query("html", description="Response format: html, htmldownload or json")
):
    """
    Generate monthly Jira report (POST endpoint).
    
    Args:
        request: Monthly report request parameters
        lang: Language for report (en, ru)
        format: Response format (html, htmldownload or json)
    
    Returns:
        HTMLResponse or JSONResponse with report data
    """
    # Override to always enable these options
    request.group_by_projects = True
    request.include_raw_data = True
    return await _generate_report(request, lang, format)


@router.get("/custom")
async def generate_custom_report_get(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    project_keys: Optional[str] = None,
    group: Optional[str] = Query(None, description="User group for report"),
    lang: str = Query("ru", description="Language for report (en, ru)"),
    format: str = Query("html", description="Response format: html, htmldownload or json")
):
    """
    Generate custom date range Jira report (GET endpoint).
    
    Args:
        start_date: Report start date (YYYY-MM-DD)
        end_date: Report end date (YYYY-MM-DD)
        project_keys: Comma-separated project keys (e.g., "PROJ1,PROJ2")
        group: User group for report (e.g., "IT")
        lang: Language for report (en, ru)
        format: Response format (html, htmldownload or json)
    
    Returns:
        HTMLResponse or JSONResponse with report data
    """
    # Parse project_keys from comma-separated string to list
    parsed_project_keys = None
    if project_keys:
        parsed_project_keys = [k.strip() for k in project_keys.split(",") if k.strip()]
    
    # Create request object with hardcoded group_by_projects=True and include_raw_data=True
    request = CustomReportRequest(
        start_date=start_date,
        end_date=end_date,
        project_keys=parsed_project_keys,
        group=group,
        group_by_projects=True,
        include_raw_data=True
    )
    
    return await _generate_custom_report(request, lang, format)


@router.post("/custom")
async def generate_custom_report_post(
    request: CustomReportRequest,
    lang: str = "ru",
    format: str = Query("html", description="Response format: html, htmldownload or json")
):
    """
    Generate custom date range Jira report (POST endpoint).
    
    Args:
        request: Custom report request parameters
        lang: Language for report (en, ru)
        format: Response format (html, htmldownload or json)
    
    Returns:
        HTMLResponse or JSONResponse with report data
    """
    # Override to always enable these options
    request.group_by_projects = True
    request.include_raw_data = True
    return await _generate_custom_report(request, lang, format)


def _build_shareable_url(request, report, is_monthly: bool = True) -> str:
    """Build a shareable URL for the report."""
    settings = get_settings()
    base_url = settings.JIRA_BASE_URL or "http://localhost:8000"
    
    if is_monthly:
        params = {
            'year': report.year,
            'month': report.month,
            'group_by_projects': 'true',
            'include_raw_data': 'true',
            'format': 'html',
            'lang': 'ru'
        }
        if request.project_keys:
            params['project_keys'] = ','.join(request.project_keys)
        if request.group:
            params['group'] = request.group
        return f"{base_url}/reports/monthly?{urlencode(params)}"
    else:
        # For custom reports, use inclusive end_date for the URL
        params = {
            'start_date': request.start_date.strftime('%Y-%m-%d'),
            'end_date': request.end_date.strftime('%Y-%m-%d'),
            'group_by_projects': 'true',
            'include_raw_data': 'true',
            'format': 'html',
            'lang': 'ru'
        }
        if request.project_keys:
            params['project_keys'] = ','.join(request.project_keys)
        if request.group:
            params['group'] = request.group
        return f"{base_url}/reports/custom?{urlencode(params)}"


async def _generate_report(request: MonthlyReportRequest, lang: str = "ru", format: str = "html"):
    """Common monthly report generation logic."""
    try:
        logger.info(
            f"Generating monthly report for {request.year}-{request.month:02d}, "
            f"projects: {request.project_keys or 'default (from ENV)'}, "
            f"group: {request.group or 'default (from ENV)'}, "
            f"group_by_projects: {request.group_by_projects}, "
            f"include_raw_data: {request.include_raw_data}, "
            f"lang: {lang}, format: {format}"
        )
        
        # Initialize services
        async with JiraClient() as jira_client:
            report_builder = ReportBuilder(jira_client)
            
            # Build report
            report = await report_builder.build_report(request)
            
            # Return based on format
            format_lower = format.lower()
            if format_lower == "json":
                return _json_response(report)
            elif format_lower == "html" or format_lower == "htmldownload":
                html_exporter = HtmlExporter(lang)
                
                html_content = html_exporter.generate(report)
                filename = f"jira_report_{request.year}_{request.month:02d}.html"
                
                if format_lower == "htmldownload":
                    return StreamingResponse(
                        io.BytesIO(html_content.encode('utf-8')),
                        media_type="text/html",
                        headers={
                            "Content-Disposition": f"attachment; filename={filename}",
                            "Content-Type": "text/html; charset=utf-8"
                        }
                    )
                return HTMLResponse(content=html_content)
    
    except Exception as e:
        logger.error(f"Failed to generate report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


async def _generate_custom_report(request: CustomReportRequest, lang: str = "ru", format: str = "html"):
    """Common custom report generation logic."""
    try:
        logger.info(
            f"Generating custom report for {request.start_date} to {request.end_date}, "
            f"projects: {request.project_keys or 'default (from ENV)'}, "
            f"group: {request.group or 'default (from ENV)'}, "
            f"group_by_projects: {request.group_by_projects}, "
            f"include_raw_data: {request.include_raw_data}, "
            f"lang: {lang}, format: {format}"
        )
        
        # Initialize services
        async with JiraClient() as jira_client:
            report_builder = ReportBuilder(jira_client)
            
            # Build custom report
            report = await report_builder.build_custom_report(request)
            
            # Return based on format
            format_lower = format.lower()
            if format_lower == "json":
                return _json_response(report)
            elif format_lower == "html" or format_lower == "htmldownload":
                html_exporter = HtmlExporter(lang)
                
                html_content = html_exporter.generate(report)
                filename = f"jira_report_{request.start_date.year}_{request.start_date.month:02d}.html"
                
                if format_lower == "htmldownload":
                    return StreamingResponse(
                        io.BytesIO(html_content.encode('utf-8')),
                        media_type="text/html",
                        headers={
                            "Content-Disposition": f"attachment; filename={filename}",
                            "Content-Type": "text/html; charset=utf-8"
                        }
                    )
                return HTMLResponse(content=html_content)
    
    except Exception as e:
        logger.error(f"Failed to generate custom report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


def _json_response(report: "ReportData"):
    """Convert report to JSON response."""
    from datetime import datetime as dt
    
    def serialize_datetime(obj):
        """Serialize datetime objects to ISO format."""
        if isinstance(obj, dt):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    # Convert report to dict and handle serialization
    report_dict = report.model_dump()
    
    # Handle datetime serialization
    def process_dict(d):
        for key, value in d.items():
            if isinstance(value, dt):
                d[key] = value.isoformat()
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        process_dict(item)
        return d
    
    report_dict = process_dict(report_dict)
    
    return JSONResponse(content=report_dict)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "jira-report"}
