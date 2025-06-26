#!/usr/bin/env python3
"""
System Health Monitor Module

Displays overall system health metrics:
- System uptime and boot time
- CPU and system temperatures (if sensors available)
- Storage health status (RAID/SMART)
"""

import os
import sys
import time
import asyncio
import psutil
import subprocess
import re
import glob
from typing import Dict, List, Tuple, Optional, Any, Set
from datetime import datetime, timedelta
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import BarColumn, Progress, TextColumn
from rich import box

# Temperature thresholds (°C)
TEMP_OK = 60
TEMP_WARN = 75
TEMP_CRITICAL = 85

# Load thresholds based on CPU count multiplier
LOAD_MULTIPLIER = 0.7  # % of CPU count considered healthy load


class SystemHealth:
    """Monitor and display system health metrics"""
    
    def __init__(self, refresh_interval: float = 1.0):
        """
        Initialize the system health monitor
        
        Args:
            refresh_interval: How often to refresh the data (in seconds)
        """
        self.refresh_interval = refresh_interval
        self.console = Console()
        self._last_update = 0
        self._cpu_count = psutil.cpu_count(logical=True)
        self._temps = {}
        self._boot_time = psutil.boot_time()
        self._raid_status = None
        self._disk_health = {}
        
        # Determine load thresholds based on CPU count
        self._load_ok = self._cpu_count * LOAD_MULTIPLIER
        self._load_warn = self._cpu_count * 1.0
        self._load_high = self._cpu_count * 1.5
        
    def update(self) -> None:
        """Update system health information"""
        current_time = time.time()
        if current_time - self._last_update >= self.refresh_interval:
            self._last_update = current_time
            
            # Update CPU and system temperatures
            self._update_temperatures()
            
            # Update storage health status
            if os.geteuid() == 0:  # Only if running as root
                self._update_raid_status()
                self._update_smart_status()
    
    def _update_temperatures(self) -> None:
        """Update temperature readings"""
        try:
            # Get temperature readings from psutil if available
            self._temps = {}
            
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                
                # Process each temperature sensor
                for chip, sensors in temps.items():
                    for sensor in sensors:
                        label = sensor.label if sensor.label else f"{chip}"
                        if hasattr(sensor, 'current') and sensor.current:
                            self._temps[label] = sensor.current
            
            # If no temps found, try reading directly from sysfs (Linux only)
            if not self._temps and os.path.exists('/sys/class/thermal'):
                thermal_zones = glob.glob('/sys/class/thermal/thermal_zone*')
                for zone in thermal_zones:
                    try:
                        with open(f"{zone}/type", 'r') as f:
                            zone_type = f.read().strip()
                            
                        with open(f"{zone}/temp", 'r') as f:
                            # Temperature is typically in millidegrees Celsius
                            temp = int(f.read().strip()) / 1000
                            self._temps[zone_type] = temp
                    except (IOError, ValueError):
                        pass
        except (AttributeError, OSError):
            # psutil sensors not available or permission denied
            pass
    
    def _update_raid_status(self) -> None:
        """Update RAID status information"""
        try:
            # Check if mdstat exists
            if os.path.exists('/proc/mdstat'):
                with open('/proc/mdstat', 'r') as f:
                    mdstat = f.read()
                    
                # Check for RAID arrays
                if 'md' in mdstat:
                    # Look for degraded arrays
                    if '[_' in mdstat or 'degraded' in mdstat:
                        self._raid_status = "DEGRADED"
                    elif 'recovery' in mdstat or 'resync' in mdstat:
                        self._raid_status = "SYNCING"
                    else:
                        self._raid_status = "OK"
                else:
                    self._raid_status = None
            else:
                self._raid_status = None
                
            # TODO: Add ZFS health check if needed
                
        except (IOError, OSError):
            self._raid_status = None
    
    def _update_smart_status(self) -> None:
        """Update disk SMART health information"""
        try:
            # Check if smartctl is available
            if not self._command_exists('smartctl'):
                return
                
            # Get list of disk devices
            disks = []
            for device in glob.glob('/dev/sd[a-z]'):
                disks.append(device)
            for device in glob.glob('/dev/nvme[0-9]n[0-9]'):
                disks.append(device)
                
            # Check SMART status for each disk
            self._disk_health = {}
            for disk in disks:
                try:
                    output = subprocess.check_output(['smartctl', '-H', disk], 
                                                   stderr=subprocess.STDOUT,
                                                   text=True)
                    
                    # Parse output for health status
                    if 'PASSED' in output:
                        status = "PASSED"
                    elif 'FAILED' in output:
                        status = "FAILED"
                    else:
                        status = "UNKNOWN"
                        
                    self._disk_health[disk] = status
                except subprocess.CalledProcessError:
                    self._disk_health[disk] = "ERROR"
                except (IOError, OSError):
                    pass
        except (IOError, OSError):
            pass
    
    def _command_exists(self, cmd: str) -> bool:
        """
        Check if a command exists in the system
        
        Args:
            cmd: Command name to check
            
        Returns:
            True if command exists, False otherwise
        """
        return subprocess.call(['which', cmd], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE) == 0
    
    def _format_uptime(self, seconds: float) -> str:
        """
        Format uptime in seconds to a human-readable string
        
        Args:
            seconds: Uptime in seconds
            
        Returns:
            Formatted uptime string (e.g., "3d 12h 45m")
        """
        delta = timedelta(seconds=seconds)
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        else:
            return f"{minutes}m {seconds}s"
    
    def _format_temperature(self, temp: float, critical: float = TEMP_CRITICAL) -> Text:
        """
        Format temperature with appropriate color based on threshold
        
        Args:
            temp: Temperature in Celsius
            critical: Critical threshold
            
        Returns:
            Formatted Rich Text object with color
        """
        formatted = Text()
        
        if temp >= TEMP_CRITICAL:
            formatted.append(f"{temp:.1f}°C", "bold red")
        elif temp >= TEMP_WARN:
            formatted.append(f"{temp:.1f}°C", "yellow")
        else:
            formatted.append(f"{temp:.1f}°C", "green")
            
        return formatted
    
    def get_table(self) -> Table:
        """
        Generate a rich table with system health information
        
        Returns:
            Rich Table object with health data
        """
        self.update()
        
        # Create a table for system health
        table = Table(
            box=box.SIMPLE,
            title="",
            show_header=True,
            header_style="bold blue",
            show_edge=False,
            padding=(0, 1),
        )
        
        # Define columns based on available data
        table.add_column("Metric", style="cyan", width=15)
        table.add_column("Value", width=20)
        table.add_column("Status", width=10)
        
        # Uptime information
        current_time = time.time()
        uptime_seconds = current_time - self._boot_time
        uptime_text = self._format_uptime(uptime_seconds)
        boot_time = datetime.fromtimestamp(self._boot_time).strftime("%Y-%m-%d %H:%M:%S")
        
        # Add uptime row
        table.add_row(
            "System Uptime",
            uptime_text,
            "[green]OK[/green]"
        )
        
        # Add boot time row
        table.add_row(
            "Boot Time",
            boot_time,
            "[green]OK[/green]"
        )
        
        # System load
        try:
            load1, load5, load15 = psutil.getloadavg()
            
            # Determine load status colors
            load1_color = "green"
            if load1 > self._load_high:
                load1_color = "red"
                load1_status = "[red]HIGH[/red]"
            elif load1 > self._load_warn:
                load1_color = "yellow"
                load1_status = "[yellow]ELEVATED[/yellow]"
            else:
                load1_color = "green"
                load1_status = "[green]NORMAL[/green]"
                
            table.add_row(
                "Load Average",
                f"[{load1_color}]{load1:.2f}[/{load1_color}] [{load5:.2f}] [{load15:.2f}]",
                load1_status
            )
        except (AttributeError, OSError):
            table.add_row(
                "Load Average",
                "N/A",
                "[yellow]UNKNOWN[/yellow]"
            )
            
        # CPU temperature (if available)
        if self._temps:
            # Find CPU temperature (look for common names)
            cpu_temp = None
            for name, temp in self._temps.items():
                if 'cpu' in name.lower() or 'core' in name.lower():
                    cpu_temp = temp
                    break
                    
            # If no specific CPU temp found, use the highest
            if cpu_temp is None and self._temps:
                cpu_temp = max(self._temps.values())
                
            if cpu_temp is not None:
                temp_text = self._format_temperature(cpu_temp)
                
                # Status based on temperature
                if cpu_temp >= TEMP_CRITICAL:
                    status = "[red]CRITICAL[/red]"
                elif cpu_temp >= TEMP_WARN:
                    status = "[yellow]WARNING[/yellow]"
                else:
                    status = "[green]NORMAL[/green]"
                    
                table.add_row(
                    "CPU Temperature",
                    str(temp_text),
                    status
                )
        
        # RAID status if available
        if self._raid_status:
            if self._raid_status == "OK":
                status_text = "[green]OK[/green]"
            elif self._raid_status == "DEGRADED":
                status_text = "[red]DEGRADED[/red]"
            elif self._raid_status == "SYNCING":
                status_text = "[yellow]SYNCING[/yellow]"
            else:
                status_text = "[yellow]UNKNOWN[/yellow]"
                
            table.add_row(
                "RAID Status",
                self._raid_status,
                status_text
            )
            
        # Add disk health
        if self._disk_health:
            for disk, status in self._disk_health.items():
                disk_name = os.path.basename(disk)
                
                if status == "PASSED":
                    status_text = "[green]HEALTHY[/green]"
                elif status == "FAILED":
                    status_text = "[red]FAILED[/red]"
                else:
                    status_text = "[yellow]UNKNOWN[/yellow]"
                    
                table.add_row(
                    f"Disk {disk_name}",
                    status,
                    status_text
                )
        
        return table
    
    def get_summary(self) -> Text:
        """
        Generate a summary of system health
        
        Returns:
            Rich Text object with health summary
        """
        self.update()
        
        # Get current uptime
        current_time = time.time()
        uptime_seconds = current_time - self._boot_time
        uptime_text = self._format_uptime(uptime_seconds)
        
        # Get load averages
        try:
            load1, load5, load15 = psutil.getloadavg()
            load_str = f"{load1:.2f}, {load5:.2f}, {load15:.2f}"
            
            # Color based on 1-min load
            if load1 > self._load_high:
                load_color = "bold red"
            elif load1 > self._load_warn:
                load_color = "yellow"
            else:
                load_color = "green"
        except (AttributeError, OSError):
            load_str = "N/A"
            load_color = "white"
        
        # Create summary text
        summary = Text()
        summary.append("System Health: ")
        summary.append(f"Up {uptime_text} ", "cyan")
        summary.append("Load: ")
        summary.append(load_str, load_color)
        
        # Add temperature if available
        if self._temps:
            cpu_temp = None
            for name, temp in self._temps.items():
                if 'cpu' in name.lower() or 'core' in name.lower():
                    cpu_temp = temp
                    break
                    
            # If no specific CPU temp found, use the highest
            if cpu_temp is None and self._temps:
                cpu_temp = max(self._temps.values())
                
            if cpu_temp is not None:
                summary.append(" | CPU: ")
                
                # Color based on temperature
                if cpu_temp >= TEMP_CRITICAL:
                    temp_color = "bold red"
                elif cpu_temp >= TEMP_WARN:
                    temp_color = "yellow"
                else:
                    temp_color = "green"
                    
                summary.append(f"{cpu_temp:.1f}°C", temp_color)
        
        return summary
    
    def get_panel(self) -> Panel:
        """
        Return a panel with system health information
        
        Returns:
            Rich Panel with table of health metrics
        """
        table = self.get_table()
        summary = self.get_summary()
        
        panel_content = Text()
        panel_content.append(summary)
        panel_content.append("\n\n")
        panel_content.append(str(table))
        
        return Panel(
            panel_content,
            title="[bold]System Health[/bold]",
            border_style="blue",
            box=box.ROUNDED
        )


async def _display_health_info() -> None:
    """Display system health information in a live view"""
    console = Console()
    monitor = SystemHealth(refresh_interval=2.0)  # Slightly longer interval for health metrics
    
    with Live(console=console, screen=True, refresh_per_second=0.5) as live:
        try:
            while True:
                panel = monitor.get_panel()
                live.update(panel)
                await asyncio.sleep(2.0)
        except KeyboardInterrupt:
            pass


def main() -> None:
    """Run the system health monitor as a standalone component"""
    try:
        if os.geteuid() != 0:
            print("[bold yellow]WARNING: Running without root privileges. Some health metrics may be limited.[/bold yellow]")
            print("[bold yellow]Try running with sudo for complete data (SMART, etc).[/bold yellow]")
        
        asyncio.run(_display_health_info())
    except KeyboardInterrupt:
        print("\nExiting System Health Monitor...")


if __name__ == "__main__":
    main()
