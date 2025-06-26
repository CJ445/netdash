#!/usr/bin/env python3
"""
Tests for the Socket Tracker module
"""

import pytest
from unittest.mock import patch, MagicMock
from netdash.socket_tracker import SocketTracker
from rich.table import Table
from rich.text import Text


@pytest.fixture
def socket_tracker():
    """Fixture for a SocketTracker instance"""
    return SocketTracker(refresh_interval=0.1)


@pytest.fixture
def mock_connections():
    """Mock connections data"""
    return [
        MagicMock(
            fd=12345,
            family=2,  # AF_INET
            type=1,    # SOCK_STREAM
            laddr=('127.0.0.1', 22),
            raddr=('192.168.1.5', 55555),
            status='ESTABLISHED',
            pid=1234
        ),
        MagicMock(
            fd=54321,
            family=10,  # AF_INET6
            type=1,     # SOCK_STREAM
            laddr=('::', 80),
            raddr=(),
            status='LISTEN',
            pid=5678
        )
    ]


@pytest.fixture
def mock_process():
    """Mock process data"""
    process = MagicMock()
    process.pid = 1234
    process.name.return_value = "sshd"
    process.username.return_value = "root"
    process.cmdline.return_value = ["/usr/sbin/sshd", "-D"]
    return process


def test_socket_tracker_initialization(socket_tracker):
    """Test that the SocketTracker initializes correctly"""
    assert socket_tracker.refresh_interval == 0.1
    assert hasattr(socket_tracker, "connections")
    assert hasattr(socket_tracker, "last_update")


@patch('psutil.net_connections')
def test_update_method(mock_net_connections, socket_tracker, mock_connections):
    """Test the update method"""
    mock_net_connections.return_value = mock_connections
    socket_tracker.update()
    assert len(socket_tracker.connections) == 2


@patch('psutil.net_connections')
@patch('psutil.Process')
def test_get_table(mock_process_class, mock_net_connections, socket_tracker, mock_connections, mock_process):
    """Test the get_table method creates a Rich Table"""
    mock_net_connections.return_value = mock_connections
    mock_process_class.return_value = mock_process
    
    socket_tracker.update()
    table = socket_tracker.get_table()
    
    assert isinstance(table, Table)
    assert "Protocol" in [col.header for col in table.columns]
    assert "Local Address" in [col.header for col in table.columns]
    assert "Remote Address" in [col.header for col in table.columns]
    assert "Status" in [col.header for col in table.columns]
    assert "PID" in [col.header for col in table.columns]
    assert "Process" in [col.header for col in table.columns]


def test_get_summary(socket_tracker):
    """Test the get_summary method creates a Rich Text object"""
    summary = socket_tracker.get_summary()
    assert isinstance(summary, Text)
    assert "connections" in summary.plain


@patch('psutil.net_connections', side_effect=PermissionError)
def test_permission_error_handling(mock_net_connections, socket_tracker):
    """Test handling of permission errors"""
    socket_tracker.update()
    table = socket_tracker.get_table()
    
    assert isinstance(table, Table)
    assert "permission" in table.caption.lower()


if __name__ == "__main__":
    pytest.main(["-v", "test_socket_tracker.py"])
