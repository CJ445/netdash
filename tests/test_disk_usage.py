#!/usr/bin/env python3
"""
Test Disk Usage Monitor Module
"""

import pytest
from netdash.disk_usage import DiskUsage


def test_disk_usage_init():
    """Test initialization of disk usage monitor"""
    monitor = DiskUsage()
    assert monitor is not None
    assert monitor.refresh_interval == 1.0
    assert isinstance(monitor.ignore_mountpoints, set)


def test_disk_usage_colors():
    """Test color calculation functions"""
    monitor = DiskUsage()
    
    # Test percentage colors
    assert monitor._get_color_for_percentage(10) == "green"
    assert monitor._get_color_for_percentage(75) == "yellow"
    assert monitor._get_color_for_percentage(85) == "dark_orange"
    assert monitor._get_color_for_percentage(95) == "red"


def test_disk_usage_format_bytes():
    """Test byte formatting function"""
    monitor = DiskUsage()
    
    assert monitor._format_bytes(1024) == "1.0 KB"
    assert monitor._format_bytes(1048576) == "1.0 MB"
    assert monitor._format_bytes(1073741824) == "1.0 GB"
    assert monitor._format_bytes(1099511627776) == "1.0 TB"


def test_disk_usage_tables():
    """Test table generation"""
    monitor = DiskUsage()
    
    filesystems_table = monitor.get_filesystems_table()
    assert filesystems_table is not None
    assert len(filesystems_table.columns) == 7
    assert filesystems_table.columns[0].header == "Filesystem"
    
    io_table = monitor.get_io_table()
    assert io_table is not None
    assert len(io_table.columns) == 5
    assert io_table.columns[0].header == "Device"
    
    combined_table = monitor.get_table()
    assert combined_table is not None


def test_disk_usage_summary():
    """Test summary generation"""
    monitor = DiskUsage()
    summary = monitor.get_summary()
    assert summary is not None
    assert "Total Storage:" in str(summary) or "Overall Usage:" in str(summary)
