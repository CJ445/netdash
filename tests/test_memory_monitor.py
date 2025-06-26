#!/usr/bin/env python3
"""
Test Memory Monitor Module
"""

import pytest
from netdash.memory_monitor import MemoryMonitor


def test_memory_monitor_init():
    """Test initialization of memory monitor"""
    monitor = MemoryMonitor()
    assert monitor is not None
    assert monitor.refresh_interval == 1.0
    assert monitor._memory_stats != {}
    assert monitor._swap_stats != {}


def test_memory_monitor_colors():
    """Test color calculation functions"""
    monitor = MemoryMonitor()
    
    # Test percentage colors
    assert monitor._get_color_for_percentage(10) == "green"
    assert monitor._get_color_for_percentage(60) == "yellow"
    assert monitor._get_color_for_percentage(80) == "dark_orange"
    assert monitor._get_color_for_percentage(95) == "red"


def test_memory_monitor_format_bytes():
    """Test byte formatting function"""
    monitor = MemoryMonitor()
    
    assert monitor._format_bytes(1024) == "1.0 KB"
    assert monitor._format_bytes(1048576) == "1.0 MB"
    assert monitor._format_bytes(1073741824) == "1.0 GB"
    assert monitor._format_bytes(1099511627776) == "1.0 TB"


def test_memory_monitor_table():
    """Test table generation"""
    monitor = MemoryMonitor()
    table = monitor.get_table()
    assert table is not None
    
    # Check if table has correct columns
    assert len(table.columns) == 4
    assert table.columns[0].header == "Memory Type"
    assert table.columns[1].header == "Size"
    assert table.columns[2].header == "Usage %"
    assert table.columns[3].header == "Usage"


def test_memory_monitor_summary():
    """Test summary generation"""
    monitor = MemoryMonitor()
    summary = monitor.get_summary()
    assert summary is not None
    assert "Total RAM" in str(summary)
    assert "Memory Usage" in str(summary)
