#!/usr/bin/env python3
"""
Tests for the Service Manager module
"""

import pytest
from unittest.mock import patch, MagicMock
from netdash.service_manager import ServiceManager
from rich.table import Table
from rich.text import Text


@pytest.fixture
def service_manager():
    """Fixture for a ServiceManager instance"""
    return ServiceManager(refresh_interval=0.1)


@pytest.fixture
def mock_services():
    """Mock systemd services data"""
    return [
        {
            "name": "ssh.service",
            "description": "OpenSSH server daemon",
            "load_state": "loaded",
            "active_state": "active",
            "sub_state": "running",
            "enabled": True,
            "unit_file_state": "enabled"
        },
        {
            "name": "apache2.service",
            "description": "The Apache HTTP Server",
            "load_state": "loaded",
            "active_state": "active",
            "sub_state": "running",
            "enabled": True,
            "unit_file_state": "enabled"
        },
        {
            "name": "mysql.service",
            "description": "MySQL Database Server",
            "load_state": "loaded",
            "active_state": "inactive",
            "sub_state": "dead",
            "enabled": False,
            "unit_file_state": "disabled"
        }
    ]


def test_service_manager_initialization(service_manager):
    """Test that the ServiceManager initializes correctly"""
    assert service_manager.refresh_interval == 0.1
    assert hasattr(service_manager, "services")


@patch('subprocess.run')
def test_update_method(mock_run, service_manager, mock_services):
    """Test the update method with mocked subprocess calls"""
    # Mock the systemctl list-units command
    process_mock = MagicMock()
    process_mock.stdout = "ssh.service loaded active running OpenSSH server daemon\napache2.service loaded active running The Apache HTTP Server\nmysql.service loaded inactive dead MySQL Database Server"
    mock_run.return_value = process_mock
    
    # Mock the systemctl is-enabled command
    side_effects = [
        MagicMock(stdout="enabled", returncode=0),
        MagicMock(stdout="enabled", returncode=0),
        MagicMock(stdout="disabled", returncode=1)
    ]
    mock_run.side_effect = side_effects
    
    service_manager.update()
    
    # Reset side effects after update
    mock_run.side_effect = None
    
    assert len(service_manager.services) == 3


@patch('subprocess.run')
def test_get_table(mock_run, service_manager):
    """Test the get_table method creates a Rich Table"""
    # Set services directly to avoid mocking subprocess
    service_manager.services = [
        {
            "name": "ssh.service",
            "description": "OpenSSH server daemon",
            "load_state": "loaded",
            "active_state": "active",
            "sub_state": "running",
            "enabled": True
        }
    ]
    
    table = service_manager.get_table()
    
    assert isinstance(table, Table)
    assert "Service" in [col.header for col in table.columns]
    assert "Status" in [col.header for col in table.columns]
    assert "Description" in [col.header for col in table.columns]


def test_get_summary(service_manager):
    """Test the get_summary method creates a Rich Text object"""
    # Set services directly
    service_manager.services = [
        {
            "name": "ssh.service",
            "active_state": "active",
            "enabled": True
        },
        {
            "name": "mysql.service",
            "active_state": "inactive",
            "enabled": False
        }
    ]
    
    summary = service_manager.get_summary()
    assert isinstance(summary, Text)


@patch('subprocess.run', side_effect=PermissionError)
def test_permission_error_handling(mock_run, service_manager):
    """Test handling of permission errors"""
    service_manager.update()
    table = service_manager.get_table()
    
    assert isinstance(table, Table)
    assert "permission" in table.caption.lower()


if __name__ == "__main__":
    pytest.main(["-v", "test_service_manager.py"])
