"""
Unit tests for configuration settings.
Tests cover Settings model, environment variable loading, and computed properties.
"""

import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError

from app.models.config import Settings, get_settings


class TestSettingsModel:
    """Tests for Settings model validation and defaults."""
    
    def test_settings_with_all_env_vars(self):
        """Test Settings with all environment variables set."""
        env_vars = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token-123",
            "JIRA_PROJECT_KEYS": "MB,MAX,IB,OPS",
            "JIRA_DONE_STATUSES": "Done,Closed,Resolved",
            "JIRA_START_STATUSES": "In Progress,In Review",
            "JIRA_BLOCKED_STATUSES": "Blocked,On Hold",
            "JIRA_EXCLUDED_STATUSES": "Repetead,Duplicate",
            "TIMEZONE": "Europe/Moscow",
            "REPORT_LANG": "en",
            "JIRA_USER_GROUP": "Developers"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None)
            
            assert settings.JIRA_BASE_URL == "https://test.atlassian.net"
            assert settings.JIRA_EMAIL == "test@example.com"
            assert settings.JIRA_API_TOKEN == "test-token-123"
            assert settings.JIRA_PROJECT_KEYS == "MB,MAX,IB,OPS"
            assert settings.REPORT_LANG == "en"
            assert settings.JIRA_USER_GROUP == "Developers"
    
    def test_settings_defaults(self):
        """Test Settings with default values."""
        env_vars = {
            "JIRA_BASE_URL": "https://default.atlassian.net",
            "JIRA_EMAIL": "default@example.com",
            "JIRA_API_TOKEN": "default-token"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None)
            
            assert settings.JIRA_PROJECT_KEYS == "MB,MAX,IB"
            assert settings.JIRA_DONE_STATUSES == "Done,Closed,Resolved"
            assert settings.JIRA_START_STATUSES == "In Progress,In Review,In Testing"
            assert settings.JIRA_BLOCKED_STATUSES == "Blocked,On Hold,Waiting"
            assert settings.JIRA_EXCLUDED_STATUSES == "Repetead"
            assert settings.TIMEZONE == "Europe/Minsk"
            assert settings.REPORT_LANG == "ru"
            assert settings.JIRA_USER_GROUP == "IT"
    
    def test_settings_missing_required_fields(self):
        """Test that missing required fields raise an error."""
        with patch.dict(os.environ, {}, clear=True):
            get_settings.cache_clear()
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            
            error_str = str(exc_info.value)
            assert "JIRA_BASE_URL" in error_str or "field required" in error_str
    
    def test_settings_partial_env_file(self):
        """Test Settings loading from .env file."""
        env_vars = {
            "JIRA_BASE_URL": "https://from-env.atlassian.net",
            "JIRA_EMAIL": "from-env@example.com",
            "JIRA_API_TOKEN": "from-env-token"
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            get_settings.cache_clear()
            settings = Settings(_env_file=".env.example")
            
            assert settings.JIRA_BASE_URL == "https://from-env.atlassian.net"


class TestSettingsComputedProperties:
    """Tests for computed properties like project_keys_list."""
    
    def test_project_keys_list_single(self):
        """Test project_keys_list with single key."""
        env_vars = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_PROJECT_KEYS": "MB"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None)
            assert settings.project_keys_list == ["MB"]
    
    def test_project_keys_list_multiple(self):
        """Test project_keys_list with multiple keys."""
        env_vars = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_PROJECT_KEYS": "MB,MAX,IB"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None)
            assert settings.project_keys_list == ["MB", "MAX", "IB"]
    
    def test_project_keys_list_with_spaces(self):
        """Test project_keys_list ignores spaces."""
        env_vars = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_PROJECT_KEYS": " MB , MAX , IB "
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None)
            assert settings.project_keys_list == ["MB", "MAX", "IB"]
    
    def test_project_keys_list_empty_string(self):
        """Test project_keys_list with empty string."""
        env_vars = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_PROJECT_KEYS": ""
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None)
            assert settings.project_keys_list == []
    
    def test_done_statuses_list(self):
        """Test done_statuses_list property."""
        env_vars = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_DONE_STATUSES": "Done,Closed"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None)
            assert settings.done_statuses_list == ["Done", "Closed"]
    
    def test_start_statuses_list(self):
        """Test start_statuses_list property."""
        env_vars = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_START_STATUSES": "In Progress"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None)
            assert settings.start_statuses_list == ["In Progress"]
    
    def test_blocked_statuses_list(self):
        """Test blocked_statuses_list property."""
        env_vars = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_BLOCKED_STATUSES": "Blocked"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None)
            assert settings.blocked_statuses_list == ["Blocked"]
    
    def test_excluded_statuses_list(self):
        """Test excluded_statuses_list property."""
        env_vars = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_EXCLUDED_STATUSES": "Repetead"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None)
            assert settings.excluded_statuses_list == ["Repetead"]
    
    def test_all_computed_properties_together(self):
        """Test all computed properties work together."""
        env_vars = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_PROJECT_KEYS": "MB,MAX",
            "JIRA_DONE_STATUSES": "Done",
            "JIRA_START_STATUSES": "In Progress",
            "JIRA_BLOCKED_STATUSES": "Blocked",
            "JIRA_EXCLUDED_STATUSES": "Repetead"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None)
            
            assert settings.project_keys_list == ["MB", "MAX"]
            assert settings.done_statuses_list == ["Done"]
            assert settings.start_statuses_list == ["In Progress"]
            assert settings.blocked_statuses_list == ["Blocked"]
            assert settings.excluded_statuses_list == ["Repetead"]


class TestGetSettingsCached:
    """Tests for get_settings cached function."""
    
    def test_get_settings_returns_settings(self):
        """Test that get_settings returns a Settings instance."""
        env_vars = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings = get_settings()
            assert isinstance(settings, Settings)
    
    def test_get_settings_caching(self):
        """Test that get_settings caches the result."""
        env_vars = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings1 = get_settings()
            settings2 = get_settings()
            assert settings1 is settings2
    
    def test_get_settings_cache_clear(self):
        """Test that cache_clear forces new instance."""
        env_vars = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings1 = get_settings()
            get_settings.cache_clear()
            settings2 = get_settings()
            assert settings1 is not settings2


class TestSettingsEdgeCases:
    """Tests for edge cases in settings."""
    
    def test_timezone_validation(self):
        """Test that invalid timezone is stored as string."""
        import zoneinfo
        
        env_vars = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "TIMEZONE": "Invalid/Timezone"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None)
            # Settings stores timezone as string without immediate validation
            assert settings.TIMEZONE == "Invalid/Timezone"
            
            # Validation happens when ZoneInfo is actually used
            with pytest.raises(zoneinfo.ZoneInfoNotFoundError):
                zoneinfo.ZoneInfo(settings.TIMEZONE)
    
    def test_report_lang_validation(self):
        """Test report language setting."""
        env_vars = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "REPORT_LANG": "en"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None)
            assert settings.REPORT_LANG == "en"
    
    def test_jira_user_group_optional(self):
        """Test that JIRA_USER_GROUP can be empty."""
        env_vars = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_USER_GROUP": ""
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None)
            assert settings.JIRA_USER_GROUP == ""
    
    def test_project_keys_with_only_spaces(self):
        """Test project keys with only spaces."""
        env_vars = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_PROJECT_KEYS": "   "
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None)
            assert settings.project_keys_list == []
