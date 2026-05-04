import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import sys

from app.api import report

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
    description="Service for generating monthly Jira reports in XLSX format",
    version="1.0.0"
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
    return templates.TemplateResponse("index.html", {"request": request})


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Jira Report Service")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Jira Report Service")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
