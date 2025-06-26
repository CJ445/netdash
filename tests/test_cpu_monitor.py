#!/usr/bin/env python3
"""
Test CPU Monitor Module
"""

import pytest
from netdash.cpu_monitor import CPUMonitor
import psutil


def test_cpu_monitor_init():
    """Test initialization of CPU monitor"""
    monitor = CPUMonitor()
    assert monitor is not None
    assert monitor.refresh_interval == 1.0
    assert len(monitor._last_cpu_percent) == psutil.cpu_count(logical=True) or len(monitor._last_cpu_percent) == 0


def test_cpu_monitor_colors():
    """Test color calculation functions"""
    monitor = CPUMonitor()
    
    # Test percentage colors
    assert monitor._get_color_for_percentage(10) == "green"
    assert monitor._get_color_for_percentage(50) == "yellow"
    assert monitor._get_color_for_percentage(80) == "dark_orange"
    assert monitor._get_color_for_percentage(95) == "red"
    
    # Test load colors (assuming 4 cores)
    assert monitor._get_color_for_load(1, 4) == "green"  # 0.25 per core
    assert monitor._get_color_for_load(3, 4) == "yellow"  # 0.75 per core
    assert monitor._get_color_for_load(5, 4) == "dark_orange"  # 1.25 per core
    assert monitor._get_color_for_load(8, 4) == "red"  # 2.0 per core


def test_cpu_monitor_table():
    """Test table generation"""
    monitor = CPUMonitor()
    table = monitor.get_table()
    assert table is not None
    
    # Check if table has correct columns
    assert len(table.columns) == 3
    assert table.columns[0].header == "Core"
    assert table.columns[1].header == "Usage %"
    assert table.columns[2].header == "Usage"


def test_cpu_monitor_summary():
    """Test summary generation"""
    monitor = CPUMonitor()
    summary = monitor.get_summary()
    assert summary is not None
    assert "CPU:" in str(summary)
    assert "Cores:" in str(summary)
