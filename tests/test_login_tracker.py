"""
Tests for the login_tracker module
"""
import pytest
from unittest.mock import patch, MagicMock
from netdash.login_tracker import LoginTracker, UserLogin
from datetime import datetime

class TestLoginTracker:
    """Test suite for LoginTracker class"""
    
    def test_initialize(self):
        """Test that login tracker initializes correctly"""
        tracker = LoginTracker()
        assert hasattr(tracker, "console")
    
    @patch('subprocess.run')
    def test_is_command_available(self, mock_run):
        """Test command availability check"""
        # Mock a successful command check
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        tracker = LoginTracker()
        assert tracker._is_command_available("who") is True
        
        # Mock a failed command check
        mock_process.returncode = 1
        assert tracker._is_command_available("nonexistent_command") is False
    
    @patch('subprocess.run')
    def test_run_command(self, mock_run):
        """Test command execution and output capture"""
        # Mock successful command execution
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "test output"
        mock_run.return_value = mock_process
        
        tracker = LoginTracker()
        success, output = tracker._run_command(["test", "command"])
        
        assert success is True
        assert output == "test output"
        
        # Mock failed command execution
        mock_process.returncode = 1
        mock_process.stderr = "error message"
        
        success, output = tracker._run_command(["test", "command"])
        
        assert success is False
        assert "error message" in output
    
    def test_parse_who_output(self):
        """Test parsing of 'who' command output"""
        sample_output = """
        user1    tty1         2023-06-26 09:30:00
        user2    pts/0        2023-06-26 10:15:00 (192.168.1.100)
        """
        
        tracker = LoginTracker()
        logins = tracker._parse_who_output(sample_output)
        
        assert len(logins) == 2
        assert logins[0].username == "user1"
        assert logins[0].tty == "tty1"
        assert logins[0].host == ""
        assert logins[0].is_active is True
        
        assert logins[1].username == "user2"
        assert logins[1].tty == "pts/0"
        assert logins[1].host == "192.168.1.100"
        assert logins[1].is_active is True
    
    def test_parse_last_output(self):
        """Test parsing of 'last' command output"""
        sample_output = """
        user1    tty1         Mon Jun 26 09:30:00 2023   still logged in
        user2    pts/0    192.168.1.100  Mon Jun 26 10:15:00 2023 - Mon Jun 26 11:20:00 2023  (01:05)
        user3    pts/1    192.168.1.101  Mon Jun 26 08:00:00 2023 - gone - no logout
        wtmp begins Tue Jun 20 00:00:00 2023
        """
        
        tracker = LoginTracker()
        logins = tracker._parse_last_output(sample_output)
        
        assert len(logins) == 3
        assert logins[0].username == "user1"
        assert logins[0].is_active is True
        
        assert logins[1].username == "user2"
        assert logins[1].is_active is False
        assert logins[1].host == "192.168.1.100"
        
        assert logins[2].username == "user3"
        assert logins[2].is_active is False
        assert logins[2].host == "192.168.1.101"
    
    @patch('netdash.login_tracker.LoginTracker.get_active_logins')
    def test_get_active_logins_table(self, mock_get_active_logins):
        """Test active logins table generation"""
        # Mock active logins
        mock_login = UserLogin(
            username="testuser",
            tty="pts/0",
            host="192.168.1.100",
            login_time=datetime(2023, 6, 26, 9, 30),
            is_active=True
        )
        mock_get_active_logins.return_value = [mock_login]
        
        tracker = LoginTracker()
        table = tracker.get_active_logins_table()
        
        # Basic verification that a table was created
        assert table is not None
        assert table.title == "Active Logins"
    
    @patch('netdash.login_tracker.LoginTracker.get_login_history')
    def test_get_login_history_table(self, mock_get_login_history):
        """Test login history table generation"""
        # Mock login history
        mock_login = UserLogin(
            username="testuser",
            tty="pts/0",
            host="192.168.1.100",
            login_time=datetime(2023, 6, 26, 9, 30),
            logout_time=datetime(2023, 6, 26, 10, 30),
            is_active=False
        )
        mock_get_login_history.return_value = [mock_login]
        
        tracker = LoginTracker()
        table = tracker.get_login_history_table()
        
        # Basic verification that a table was created
        assert table is not None
        assert "Recent Logins" in table.title
