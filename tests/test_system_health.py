#!/usr/bin/env python3
"""
Tests for the System Health module
"""

import pytest
from unittest.mock import patch, MagicMock
from netdash.system_health import SystemHealth
from rich.table import Table
from rich.text import Text


@pytest.fixture
def system_health():
    """Fixture for a SystemHealth instance"""
    return SystemHealth(refresh_interval=0.1)


@pytest.fixture
def mock_uptime():
    """Mock uptime data"""
    return 345678.90  # seconds


@pytest.fixture
def mock_load():
    """Mock load averages data"""
    return (1.25, 1.15, 1.05)


@pytest.fixture
def mock_temps():
    """Mock temperature data"""
    mock = MagicMock()
    mock.current = 45.5
    mock.high = 90.0
    mock.critical = 105.0
    mock.label = "CPU"
    return {"coretemp": [mock]}


@pytest.fixture
def mock_raid():
    """Mock RAID status data"""
    return [
        {
            "device": "/dev/md0",
            "status": "active",
            "level": "raid1",
            "size": "931.51GB",
            "disks": ["sda1", "sdb1"],
            "health": "healthy"
        }
    ]


@pytest.fixture
def mock_smart():
    """Mock SMART data"""
    return {
        "/dev/sda": {
            "health": "PASSED",
            "temp": 35,
            "power_on_hours": 8760,  # 1 year
            "reallocated_sectors": 0
        },
        "/dev/sdb": {
            "health": "PASSED",
            "temp": 37,
            "power_on_hours": 4380,  # 6 months
            "reallocated_sectors": 0
        }
    }


def test_system_health_initialization(system_health):
    """Test that the SystemHealth initializes correctly"""
    assert system_health.refresh_interval == 0.1
    assert hasattr(system_health, "uptime")
    assert hasattr(system_health, "load_avg")


@patch('psutil.boot_time')
@patch('time.time')
@patch('os.getloadavg')
def test_update_method(mock_getloadavg, mock_time, mock_boot_time, system_health, mock_load):
    """Test the update method"""
    mock_boot_time.return_value = 0
    mock_time.return_value = 345678.90
    mock_getloadavg.return_value = mock_load
    
    system_health.update()
    
    assert system_health.uptime == 345678.90
    assert system_health.load_avg == mock_load


@patch('psutil.boot_time')
@patch('time.time')
@patch('os.getloadavg')
def test_get_table(mock_getloadavg, mock_time, mock_boot_time, system_health, mock_load):
    """Test the get_table method creates a Rich Table"""
    mock_boot_time.return_value = 0
    mock_time.return_value = 345678.90
    mock_getloadavg.return_value = mock_load
    
    system_health.update()
    table = system_health.get_table()
    
    assert isinstance(table, Table)
    assert table.title is not None


def test_get_summary(system_health):
    """Test the get_summary method creates a Rich Text object"""
    summary = system_health.get_summary()
    assert isinstance(summary, Text)


@patch('psutil.boot_time', side_effect=PermissionError)
def test_permission_error_handling(mock_boot_time, system_health):
    """Test handling of permission errors"""
    system_health.update()
    table = system_health.get_table()
    
    assert isinstance(table, Table)


if __name__ == "__main__":
    pytest.main(["-v", "test_system_health.py"])
