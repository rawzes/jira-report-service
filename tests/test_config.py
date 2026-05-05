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
            "JIRA_PROJECT_KEYS": "MB,MAX,IB",
            "JIRA_DONE_STATUSES": "Done,Closed,Resolved",
            "JIRA_START_STATUSES": "In Progress,In Review",
            "JIRA_BLOCKED_STATUSES": "Blocked,On Hold",
            "JIRA_EXCLUDED_STATUSES": "Repetead,Duplicate",
            "TIMEZONE": "Europe/Moscow",
            "REPORT_LANG": "en",
            "JIRA_USER_GROUP": "Developers"
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            # Clear lru_cache to get fresh settings
            get_settings.cache_clear()
            settings = Settings()
            
            assert settings.JIRA_BASE_URL == "https://test.atlassian.net"
            assert settings.JIRA_EMAIL == "test@example.com"
            assert settings.JIRA_API_TOKEN == "test-token-123"
            assert settings.JIRA_PROJECT_KEYS == "MB,MAX,IB"
            assert settings.REPORT_LANG == "en"
            assert settings.JIRA_USER_GROUP == "Developers"

    def test_settings_defaults(self):
        """Test Settings with default values."""
        env_vars = {
            "JIRA_BASE_URL": "https://default.atlassian.net",
            "JIRA_EMAIL": "default@example.com",
            "JIRA_API_TOKEN": "default-token"
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            get_settings.cache_clear()
            settings = Settings()
            
            # Check defaults
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
        # Remove required env vars
        env_vars = {}
        
        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            # Should raise ValidationError for missing required fields
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            # Check that the error mentions the missing fields
            error_str = str(exc_info.value)
            assert "JIRA_BASE_URL" in error_str or "field required" in error_str

    def test_settings_partial_env_file(self):
        """Test Settings loading from .env file."""
        # This test verifies the Settings can load from .env
        # In practice, we mock the environment
        env_vars = {
            "JIRA_BASE_URL": "https://from-env.atlassian.net",
            "JIRA_EMAIL": "from-env@example.com",
            "JIRA_API_TOKEN": "from-env-token"
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            get_settings.cache_clear()
            settings = Settings(_env_file=".env.example")  # Use example file
            
            # Should still use env vars if present
            assert settings.JIRA_BASE_URL == "https://from-env.atlassian.net"


class TestSettingsComputedProperties:
    """Tests for computed properties (project_keys_list, done_statuses_list, etc.)."""

    def test_project_keys_list_single(self):
        """Test project_keys_list with single project."""
        with patch.dict(os.environ, {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_PROJECT_KEYS": "MB"
        }):
            get_settings.cache_clear()
            settings = Settings()
            assert settings.project_keys_list == ["MB"]

    def test_project_keys_list_multiple(self):
        """Test project_keys_list with multiple projects."""
        with patch.dict(os.environ, {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_PROJECT_KEYS": "MB, MAX, IB"
        }):
            get_settings.cache_clear()
            settings = Settings()
            assert settings.project_keys_list == ["MB", "MAX", "IB"]

    def test_project_keys_list_with_spaces(self):
        """Test project_keys_list handles spaces correctly."""
        with patch.dict(os.environ, {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_PROJECT_KEYS": " MB , MAX , IB "
        }):
            get_settings.cache_clear()
            settings = Settings()
            assert settings.project_keys_list == ["MB", "MAX", "IB"]

    def test_project_keys_list_empty_string(self):
        """Test project_keys_list with empty string."""
        with patch.dict(os.environ, {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_PROJECT_KEYS": ""
        }):
            get_settings.cache_clear()
            settings = Settings()
            assert settings.project_keys_list == []

    def test_done_statuses_list(self):
        """Test done_statuses_list property."""
        with patch.dict(os.environ, {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_DONE_STATUSES": "Done, Closed, Resolved"
        }):
            get_settings.cache_clear()
            settings = Settings()
            assert settings.done_statuses_list == ["Done", "Closed", "Resolved"]

    def test_start_statuses_list(self):
        """Test start_statuses_list property."""
        with patch.dict(os.environ, {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_START_STATUSES": "In Progress, In Review"
        }):
            get_settings.cache_clear()
            settings = Settings()
            assert settings.start_statuses_list == ["In Progress", "In Review"]

    def test_blocked_statuses_list(self):
        """Test blocked_statuses_list property."""
        with patch.dict(os.environ, {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_BLOCKED_STATUSES": "Blocked, On Hold, Waiting"
        }):
            get_settings.cache_clear()
            settings = Settings()
            assert settings.blocked_statuses_list == ["Blocked", "On Hold", "Waiting"]

    def test_excluded_statuses_list(self):
        """Test excluded_statuses_list property."""
        with patch.dict(os.environ, {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_EXCLUDED_STATUSES": "Repetead, Duplicates"
        }):
            get_settings.cache_clear()
            settings = Settings()
            assert settings.excluded_statuses_list == ["Repetead", "Duplicates"]

    def test_all_computed_properties_together(self):
        """Test all computed properties work together."""
        with patch.dict(os.environ, {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_PROJECT_KEYS": "MB,MAX",
            "JIRA_DONE_STATUSES": "Done",
            "JIRA_START_STATUSES": "In Progress",
            "JIRA_BLOCKED_STATUSES": "Blocked",
            "JIRA_EXCLUDED_STATUSES": "Repetead"
        }):
            get_settings.cache_clear()
            settings = Settings()
            
            assert settings.project_keys_list == ["MB", "MAX"]
            assert settings.done_statuses_list == ["Done"]
            assert settings.start_statuses_list == ["In Progress"]
            assert settings.blocked_statuses_list == ["Blocked"]
            assert settings.excluded_statuses_list == ["Repetead"]


class TestGetSettingsCached:
    """Tests for get_settings cached function."""

    def test_get_settings_returns_settings(self):
        """Test that get_settings returns a Settings instance."""
        with patch.dict(os.environ, {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token"
        }):
            get_settings.cache_clear()
            settings = get_settings()
            assert isinstance(settings, Settings)

    def test_get_settings_caching(self):
        """Test that get_settings caches the result."""
        with patch.dict(os.environ, {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token"
        }):
            get_settings.cache_clear()
            settings1 = get_settings()
            settings2 = get_settings()
            
            # Should be the same object (cached)
            assert settings1 is settings2

    def test_get_settings_cache_clear(self):
        """Test that cache can be cleared."""
        with patch.dict(os.environ, {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token"
        }):
            get_settings.cache_clear()
            settings1 = get_settings()
            
            get_settings.cache_clear()
            settings2 = get_settings()
            
            # After cache clear, should be different objects
            assert settings1 is not settings2


class TestSettingsEdgeCases:
    """Tests for edge cases in Settings."""

    def test_timezone_validation(self):
        """Test timezone setting."""
        with patch.dict(os.environ, {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "TIMEZONE": "Europe/London"
        }):
            get_settings.cache_clear()
            settings = Settings()
            assert settings.TIMEZONE == "Europe/London"

    def test_report_lang_validation(self):
        """Test report language setting."""
        with patch.dict(os.environ, {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "REPORT_LANG": "en"
        }):
            get_settings.cache_clear()
            settings = Settings()
            assert settings.REPORT_LANG == "en"

    def test_jira_user_group_optional(self):
        """Test that JIRA_USER_GROUP can be empty."""
        with patch.dict(os.environ, {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_USER_GROUP": ""
        }):
            get_settings.cache_clear()
            settings = Settings()
            assert settings.JIRA_USER_GROUP == ""

    def test_project_keys_with_only_spaces(self):
        """Test project keys with only spaces."""
        with patch.dict(os.environ, {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@example.com",
            "JIRA_API_TOKEN": "test-token",
            "JIRA_PROJECT_KEYS": "   ,   ,   "
        }):
            get_settings.cache_clear()
            settings = Settings()
            # Should filter out empty strings
            result = settings.project_keys_list
            assert all(k.strip() != "" for k in result)
