import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import sys

from app.api import report
from app.models.config import get_settings

# Configure templates
templates = Jinja2Templates(directory="app/templates")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Jira Report Service",
    description="Service for generating Jira reports in HTML format",
    version="1.0.0",
    redoc_url=None,  # Disable default ReDoc
    docs_url="/docs"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(report.router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main page with report generation form."""
    settings = get_settings()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "REPORT_LANG": settings.REPORT_LANG,
        "JIRA_PROJECT_KEYS": settings.JIRA_PROJECT_KEYS,
        "JIRA_USER_GROUP": settings.JIRA_USER_GROUP
    })


@app.get("/redoc", response_class=HTMLResponse)
async def custom_redoc():
    """Custom ReDoc page with working CDN."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Jira Report Service - ReDoc</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
        <style>
            body { margin: 0; padding: 0; }
        </style>
    </head>
    <body>
        <redoc spec-url="/openapi.json"></redoc>
        <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Jira Report Service")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Jira Report Service")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
