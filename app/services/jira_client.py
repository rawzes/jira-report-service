import asyncio
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime, timedelta
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tenacity import before_log, after_log
import time

from app.models.config import get_settings

logger = logging.getLogger(__name__)


class JiraApiError(Exception):
    """Custom exception for Jira API errors."""
    pass


class JiraRateLimitError(JiraApiError):
    """Exception for rate limit errors."""
    pass


class JiraClient:
    """Client for Jira Cloud REST API with retry logic and rate limiting."""
    
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.JIRA_BASE_URL.rstrip("/")
        self.email = settings.JIRA_EMAIL
        self.api_token = settings.JIRA_API_TOKEN
        self._client: Optional[httpx.AsyncClient] = None
        self._semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
        
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=(self.email, self.api_token),
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={"Accept": "application/json", "Content-Type": "application/json"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        before=before_log(logger, logging.DEBUG),
        after=after_log(logger, logging.DEBUG)
    )
    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        async with self._semaphore:
            try:
                response = await self._client.request(method, url, **kwargs)
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds.")
                    await asyncio.sleep(retry_after)
                    raise JiraRateLimitError("Rate limited")
                
                response.raise_for_status()
                return response
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds.")
                    await asyncio.sleep(retry_after)
                    raise JiraRateLimitError("Rate limited")
                logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
                raise
    
    async def search_issues_jql(
        self,
        jql: str,
        fields: Optional[List[str]] = None,
        max_results: int = 100,
        expand: Optional[List[str]] = None
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Search issues using JQL with pagination via nextPageToken.
        
        Args:
            jql: JQL query string
            fields: List of fields to return
            max_results: Maximum results per page
            expand: List of fields to expand (e.g., ['changelog'])
            
        Yields:
            List of issues per page
        """
        url = "/rest/api/3/search/jql"
        params = {
            "jql": jql,
            "maxResults": max_results
        }
        if fields:
            params["fields"] = fields
        if expand:
            params["expand"] = ",".join(expand)
        
        while True:
            response = await self._make_request("POST", url, json=params)
            data = response.json()
            
            issues = data.get("issues", [])
            if issues:
                yield issues
            
            # Check for next page
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
            
            params["nextPageToken"] = next_page_token
    
    async def get_issue_changelog(
        self,
        issue_key: str
    ) -> Dict[str, Any]:
        """
        Get issue with full changelog history.
        Handles pagination of changelog if present.
        
        Args:
            issue_key: Issue key (e.g., 'MB-123')
            
        Returns:
            Issue data with complete changelog
        """
        url = f"/rest/api/3/issue/{issue_key}"
        params = {
            "expand": "changelog"
        }
        
        response = await self._make_request("GET", url, params=params)
        issue_data = response.json()
        
        # Handle paginated changelog
        changelog = issue_data.get("changelog", {})
        all_histories = changelog.get("histories", [])
        
        # Check if there are more pages (some Jira instances paginate changelog)
        while changelog.get("isLast") is False:
            start_at = changelog.get("startAt", 0) + len(all_histories)
            params["startAt"] = start_at
            
            response = await self._make_request("GET", url, params=params)
            page_data = response.json()
            changelog = page_data.get("changelog", {})
            all_histories.extend(changelog.get("histories", []))
        
        # Update the issue data with complete changelog
        if "changelog" not in issue_data:
            issue_data["changelog"] = {}
        issue_data["changelog"]["histories"] = all_histories
        
        return issue_data
    
    async def get_issue_worklogs(
        self,
        issue_key: str
    ) -> List[Dict[str, Any]]:
        """
        Get all worklogs for an issue with pagination.
        
        Args:
            issue_key: Issue key (e.g., 'MB-123')
            
        Returns:
            List of all worklog entries
        """
        url = f"/rest/api/3/issue/{issue_key}/worklog"
        all_worklogs = []
        start_at = 0
        max_results = 1000
        
        while True:
            params = {"startAt": start_at, "maxResults": max_results}
            response = await self._make_request("GET", url, params=params)
            data = response.json()
            
            worklogs = data.get("worklogs", [])
            all_worklogs.extend(worklogs)
            
            # Check if we have more pages
            total = data.get("total", 0)
            if start_at + len(worklogs) >= total:
                break
            
            start_at += len(worklogs)
        
        return all_worklogs
    
    async def get_worklog_updated(
        self,
        since: Optional[int] = None,
        until: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get worklog IDs updated in a time range (incremental sync).
        
        Args:
            since: Unix timestamp in milliseconds
            until: Unix timestamp in milliseconds
            
        Returns:
            Dict with worklog IDs and pagination info
        """
        url = "/rest/api/3/worklog/updated"
        params = {}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        
        response = await self._make_request("GET", url, params=params)
        return response.json()
    
    async def get_worklogs_by_ids(
        self,
        worklog_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Get worklog details by IDs (for incremental sync).
        
        Args:
            worklog_ids: List of worklog IDs
            
        Returns:
            List of worklog details
        """
        url = "/rest/api/3/worklog/list"
        response = await self._make_request("POST", url, json={"ids": worklog_ids})
        return response.json()
    
    def build_created_jql(
        self,
        project_keys: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """Build JQL for issues created in date range."""
        projects = ", ".join([f'"{k}"' for k in project_keys])
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        return f"project in ({projects}) AND created >= '{start_str}' AND created < '{end_str}'"
    
    def build_done_jql(
        self,
        project_keys: List[str],
        start_date: datetime,
        end_date: datetime,
        done_statuses: List[str]
    ) -> str:
        """Build JQL for issues closed in date range."""
        projects = ", ".join([f'"{k}"' for k in project_keys])
        statuses = ", ".join([f'"{s}"' for s in done_statuses])
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        return (
            f"project in ({projects}) AND status in ({statuses}) "
            f"AND statusCategoryChangedDate >= '{start_str}' "
            f"AND statusCategoryChangedDate < '{end_str}'"
        )
    
    def build_worklog_jql(
        self,
        project_keys: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """Build JQL for issues with worklog in date range."""
        projects = ", ".join([f'"{k}"' for k in project_keys])
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        return (
            f"project in ({projects}) AND worklogDate >= '{start_str}' "
            f"AND worklogDate < '{end_str}'"
        )
    
    def build_all_issues_jql(
        self,
        project_keys: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """Build JQL for all issues relevant to the report (created or updated in range)."""
        projects = ", ".join([f'"{k}"' for k in project_keys])
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        return (
            f"project in ({projects}) AND "
            f"(created >= '{start_str}' OR updated >= '{start_str}') "
            f"AND created < '{end_str}'"
        )
    
    async def get_group_members(
        self,
        group_name: str,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get members of a Jira group.
        
        Args:
            group_name: Name of the Jira group
            max_results: Maximum results per page
            
        Returns:
            List of user objects in the group
        """
        url = "/rest/api/3/group/member"
        params = {
            "groupname": group_name,
            "maxResults": max_results
        }
        
        all_members = []
        
        while True:
            response = await self._make_request("GET", url, params=params)
            data = response.json()
            
            members = data.get("values", [])
            all_members.extend(members)
            
            # Check for pagination
            if data.get("isLast", True):
                break
                
            params["startAt"] = data.get("startAt", 0) + len(members)
        
        return all_members
