from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    JIRA_BASE_URL: str
    JIRA_EMAIL: str
    JIRA_API_TOKEN: str
    JIRA_PROJECT_KEYS: str = "MB,MAX,IB"
    JIRA_DONE_STATUSES: str = "Done,Closed,Resolved"
    JIRA_START_STATUSES: str = "In Progress,In Review,In Testing"
    JIRA_BLOCKED_STATUSES: str = "Blocked,On Hold,Waiting"
    JIRA_EXCLUDED_STATUSES: str = "Repetead"
    TIMEZONE: str = "Europe/Minsk"
    REPORT_LANG: str = "ru"
    
    # Computed properties
    @property
    def project_keys_list(self) -> List[str]:
        return [k.strip() for k in self.JIRA_PROJECT_KEYS.split(",") if k.strip()]
    
    @property
    def done_statuses_list(self) -> List[str]:
        return [s.strip() for s in self.JIRA_DONE_STATUSES.split(",") if s.strip()]
    
    @property
    def start_statuses_list(self) -> List[str]:
        return [s.strip() for s in self.JIRA_START_STATUSES.split(",") if s.strip()]
    
    @property
    def blocked_statuses_list(self) -> List[str]:
        return [s.strip() for s in self.JIRA_BLOCKED_STATUSES.split(",") if s.strip()]
    
    @property
    def excluded_statuses_list(self) -> List[str]:
        return [s.strip() for s in self.JIRA_EXCLUDED_STATUSES.split(",") if s.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
