"""
Tests for the log_monitor module
"""
import pytest
from unittest.mock import patch, MagicMock, mock_open
import os
from datetime import datetime
from netdash.log_monitor import LogMonitor, LogEvent, LogMonitorConfig

class TestLogMonitor:
    """Test suite for LogMonitor class"""
    
    def test_initialize_with_default_config(self):
        """Test initialization with default configuration"""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            monitor = LogMonitor()
            assert monitor.log_source == "dummy"
    
    def test_initialize_with_existing_log_file(self):
        """Test initialization with valid log file"""
        with patch('os.path.exists') as mock_exists, \
             patch('os.access') as mock_access:
            mock_exists.return_value = True
            mock_access.return_value = True
            
            config = LogMonitorConfig(log_file="/test/log/file")
            monitor = LogMonitor(config)
            
            assert monitor.log_source == "file"
            assert monitor.config.log_file == "/test/log/file"
    
    def test_initialize_with_journalctl(self):
        """Test initialization with journalctl"""
        with patch('os.path.exists') as mock_exists, \
             patch('netdash.log_monitor.LogMonitor._is_command_available') as mock_cmd_available:
            mock_exists.return_value = False
            mock_cmd_available.return_value = True
            
            config = LogMonitorConfig(log_file="/nonexistent/file", journal_unit="test.service")
            monitor = LogMonitor(config)
            
            assert monitor.log_source == "journalctl"
            assert monitor.config.journal_unit == "test.service"
    
    @patch('netdash.log_monitor.LogMonitor._is_command_available')
    @patch('netdash.log_monitor.LogMonitor._run_command')
    def test_tail_file(self, mock_run_command, mock_cmd_available):
        """Test file tailing functionality"""
        mock_cmd_available.return_value = True
        mock_run_command.return_value = (True, "line1\nline2\nline3")
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            config = LogMonitorConfig(log_file="/test/log/file")
            monitor = LogMonitor(config)
            
            lines = monitor._tail_file(3)
            assert len(lines) == 3
            assert lines[0] == "line1"
    
    @patch('netdash.log_monitor.LogMonitor._is_command_available')
    @patch('netdash.log_monitor.LogMonitor._run_command')
    def test_get_journalctl_logs(self, mock_run_command, mock_cmd_available):
        """Test journalctl log retrieval"""
        mock_cmd_available.return_value = True
        mock_run_command.return_value = (True, "line1\nline2\nline3")
        
        config = LogMonitorConfig(journal_unit="test.service")
        monitor = LogMonitor(config)
        
        lines = monitor._get_journalctl_logs(3)
        assert len(lines) == 3
        assert lines[0] == "line1"
        
        # Verify journalctl command parameters
        mock_run_command.assert_called_with(
            ["journalctl", "-n", "3", "--no-pager", "-u", "test.service"]
        )
    
    def test_parse_log_line_syslog_format(self):
        """Test parsing standard syslog formatted line"""
        line = "Jun 26 09:30:01 hostname sshd[1234]: Failed password for user root from 192.168.1.100"
        
        monitor = LogMonitor()
        event = monitor._parse_log_line(line)
        
        assert event is not None
        assert event.source == "sshd"
        assert "Failed password for user root" in event.message
        assert event.alert is True  # Should match the failed_login pattern
        assert event.level == "ERROR"
    
    def test_parse_log_line_iso_format(self):
        """Test parsing ISO formatted timestamp"""
        line = "2023-06-26T09:30:01 hostname sudo[1234]: user : COMMAND=/usr/bin/something"
        
        monitor = LogMonitor()
        event = monitor._parse_log_line(line)
        
        assert event is not None
        assert event.source == "sudo"
        assert "user : COMMAND=" in event.message
        assert event.alert is True  # Should match the sudo_usage pattern
        assert event.level == "WARNING"
    
    def test_alert_detection(self):
        """Test alert pattern detection"""
        monitor = LogMonitor()
        
        # Test failed login alert
        failed_login = "Jun 26 09:30:01 hostname sshd[1234]: Failed password for invalid user"
        event = monitor._parse_log_line(failed_login)
        assert event.alert is True
        assert event.level == "ERROR"
        
        # Test sudo usage alert
        sudo_usage = "Jun 26 09:30:01 hostname sudo[1234]: user : COMMAND=/usr/bin/something"
        event = monitor._parse_log_line(sudo_usage)
        assert event.alert is True
        assert event.level == "WARNING"
        
        # Test SSH login alert
        ssh_login = "Jun 26 09:30:01 hostname sshd[1234]: Accepted password for user from 192.168.1.100"
        event = monitor._parse_log_line(ssh_login)
        assert event.alert is True
        
        # Test non-alert message
        normal = "Jun 26 09:30:01 hostname systemd[1]: Starting Service..."
        event = monitor._parse_log_line(normal)
        assert event.alert is False
        assert event.level == "INFO"
    
    def test_get_alert_count(self):
        """Test alert counting by type"""
        monitor = LogMonitor()
        
        # Create test events
        monitor.events = [
            LogEvent(
                timestamp=datetime.now(),
                source="sshd",
                message="Failed password for invalid user",
                raw_line="Jun 26 09:30:01 hostname sshd[1234]: Failed password for invalid user",
                level="ERROR",
                alert=True
            ),
            LogEvent(
                timestamp=datetime.now(),
                source="sshd",
                message="Failed password for invalid user",
                raw_line="Jun 26 09:30:02 hostname sshd[1234]: Failed password for invalid user",
                level="ERROR",
                alert=True
            ),
            LogEvent(
                timestamp=datetime.now(),
                source="sudo",
                message="user : COMMAND=/usr/bin/something",
                raw_line="Jun 26 09:30:03 hostname sudo[1234]: user : COMMAND=/usr/bin/something",
                level="WARNING",
                alert=True
            ),
            LogEvent(
                timestamp=datetime.now(),
                source="systemd",
                message="Starting Service...",
                raw_line="Jun 26 09:30:04 hostname systemd[1]: Starting Service...",
                level="INFO",
                alert=False
            )
        ]
        
        counts = monitor.get_alert_count()
        assert counts["failed_login"] == 2
        assert counts["sudo_usage"] == 1
        assert counts["ssh_login"] == 0
