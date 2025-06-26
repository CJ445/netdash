#!/usr/bin/env python3
"""
Disk Usage Monitor Module

Displays detailed disk usage information:
- Per-device I/O statistics (read/write ops/sec)
- Filesystem usage percentage with alerts
- Mount points and available space
"""

import os
import sys
import time
import asyncio
import psutil
import shutil
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime, timedelta
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import BarColumn, Progress, TextColumn
from rich import box

# Color thresholds for disk utilization
WARN_THRESHOLD = 70
CRITICAL_THRESHOLD = 80
DANGER_THRESHOLD = 90


class DiskUsage:
    """Monitor and display disk usage information"""
    
    def __init__(self, refresh_interval: float = 1.0, ignore_mountpoints: Optional[Set[str]] = None):
        """
        Initialize the disk usage monitor
        
        Args:
            refresh_interval: How often to refresh the data (in seconds)
            ignore_mountpoints: Set of mountpoints to ignore
        """
        self.refresh_interval = refresh_interval
        self.console = Console()
        self._last_update = 0
        self._last_io_counters = {}
        self._io_rates = {}
        self.ignore_mountpoints = ignore_mountpoints or {'/proc', '/sys', '/run', '/dev', '/snap'}
        self.update()
    
    def update(self) -> None:
        """Update disk statistics"""
        current_time = time.time()
        
        # Only update if refresh interval has elapsed
        if current_time - self._last_update >= self.refresh_interval:
            # Get disk I/O counters
            current_io_counters = psutil.disk_io_counters(perdisk=True)
            
            # Calculate I/O rates
            if self._last_io_counters and (current_time - self._last_update > 0):
                interval = current_time - self._last_update
                
                for disk in current_io_counters:
                    if disk in self._last_io_counters:
                        prev = self._last_io_counters[disk]
                        curr = current_io_counters[disk]
                        
                        read_ops = (curr.read_count - prev.read_count) / interval
                        write_ops = (curr.write_count - prev.write_count) / interval
                        read_bytes = (curr.read_bytes - prev.read_bytes) / interval
                        write_bytes = (curr.write_bytes - prev.write_bytes) / interval
                        
                        self._io_rates[disk] = {
                            'read_ops': read_ops,
                            'write_ops': write_ops,
                            'read_bytes': read_bytes,
                            'write_bytes': write_bytes
                        }
            
            self._last_io_counters = current_io_counters
            self._last_update = current_time
    
    def _get_color_for_percentage(self, percent: float) -> str:
        """
        Get the color based on the percentage value
        
        Args:
            percent: Disk utilization percentage
            
        Returns:
            Color string for rich
        """
        if percent < WARN_THRESHOLD:
            return "green"
        elif percent < CRITICAL_THRESHOLD:
            return "yellow"
        elif percent < DANGER_THRESHOLD:
            return "dark_orange"
        else:
            return "red"
    
    def _format_bytes(self, bytes_value: int) -> str:
        """
        Format bytes to human-readable form
        
        Args:
            bytes_value: Bytes to format
            
        Returns:
            Formatted string (e.g., "4.2 GB")
        """
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        value = float(bytes_value)
        
        while value >= 1024 and unit_index < len(units) - 1:
            value /= 1024
            unit_index += 1
        
        return f"{value:.1f} {units[unit_index]}"
    
    def _format_bytes_per_sec(self, bytes_value: float) -> str:
        """Format bytes/sec to human-readable form"""
        return f"{self._format_bytes(bytes_value)}/s"
    
    def get_summary(self) -> Text:
        """
        Get a summary of disk information
        
        Returns:
            Rich Text object with disk summary
        """
        self.update()
        
        text = Text()
        
        # Add total disk space
        total = 0
        used = 0
        
        for part in psutil.disk_partitions(all=False):
            if part.mountpoint in self.ignore_mountpoints:
                continue
                
            try:
                usage = psutil.disk_usage(part.mountpoint)
                total += usage.total
                used += usage.used
            except (PermissionError, FileNotFoundError):
                pass
        
        if total > 0:
            overall_percent = (used / total) * 100
            text.append(f"Total Storage: {self._format_bytes(total)}\n")
            
            color = self._get_color_for_percentage(overall_percent)
            text.append("Overall Usage: ")
            text.append(f"{overall_percent:.1f}%", style=f"bold {color}")
        
        # Add I/O summary
        read_bytes_total = 0
        write_bytes_total = 0
        
        for disk, rates in self._io_rates.items():
            read_bytes_total += rates.get('read_bytes', 0)
            write_bytes_total += rates.get('write_bytes', 0)
        
        if read_bytes_total > 0 or write_bytes_total > 0:
            text.append("\n")
            text.append(f"Read: {self._format_bytes_per_sec(read_bytes_total)}, ")
            text.append(f"Write: {self._format_bytes_per_sec(write_bytes_total)}")
        
        return text
    
    def get_filesystems_table(self) -> Table:
        """
        Get a table of filesystem usage
        
        Returns:
            Rich Table object with filesystem usage
        """
        self.update()
        
        # Create table
        table = Table(
            box=box.SIMPLE_HEAVY,
            expand=True,
            show_header=True,
            header_style="bold white"
        )
        
        # Add columns
        table.add_column("Filesystem", style="cyan", no_wrap=True)
        table.add_column("Type", style="bright_black", width=8)
        table.add_column("Size", justify="right", width=10)
        table.add_column("Used", justify="right", width=10)
        table.add_column("Avail", justify="right", width=10)
        table.add_column("Use%", justify="right", width=6)
        table.add_column("Usage", ratio=1)
        
        # Get partition information
        partitions = psutil.disk_partitions(all=False)
        partitions.sort(key=lambda p: p.mountpoint)
        
        for part in partitions:
            if part.mountpoint in self.ignore_mountpoints:
                continue
            
            try:
                usage = psutil.disk_usage(part.mountpoint)
                percent = usage.percent
                color = self._get_color_for_percentage(percent)
                
                # Create usage bar
                bar_width = 30  # Fixed width for the bar
                filled = int(percent / 100 * bar_width)
                usage_bar = "█" * filled + "░" * (bar_width - filled)
                
                # Get filesystem type
                fs_type = part.fstype
                if len(fs_type) > 7:
                    fs_type = fs_type[:7]
                
                # Add row
                table.add_row(
                    part.mountpoint,
                    fs_type,
                    self._format_bytes(usage.total),
                    self._format_bytes(usage.used),
                    self._format_bytes(usage.free),
                    f"{percent:.1f}%",
                    Text(usage_bar, style=color)
                )
            except (PermissionError, FileNotFoundError):
                pass
        
        return table
    
    def get_io_table(self) -> Table:
        """
        Get a table of disk I/O statistics
        
        Returns:
            Rich Table object with disk I/O statistics
        """
        self.update()
        
        # Create table
        table = Table(
            box=box.SIMPLE_HEAVY,
            expand=True,
            show_header=True,
            header_style="bold white"
        )
        
        # Add columns
        table.add_column("Device", style="cyan")
        table.add_column("Read", justify="right", style="green")
        table.add_column("Write", justify="right", style="yellow")
        table.add_column("Read ops/s", justify="right", style="green")
        table.add_column("Write ops/s", justify="right", style="yellow")
        
        # Add rows for each disk
        for disk, rates in sorted(self._io_rates.items()):
            table.add_row(
                disk,
                self._format_bytes_per_sec(rates.get('read_bytes', 0)),
                self._format_bytes_per_sec(rates.get('write_bytes', 0)),
                f"{rates.get('read_ops', 0):.1f}",
                f"{rates.get('write_ops', 0):.1f}"
            )
        
        return table
    
    def get_table(self) -> Table:
        """
        Get combined disk usage and I/O tables
        
        Returns:
            Rich Table object
        """
        # Create layout with filesystem and I/O tables
        filesystems_table = self.get_filesystems_table()
        io_table = self.get_io_table()
        
        # Create a table to hold both
        main_table = Table.grid(expand=True, padding=(0, 1))
        main_table.add_row(filesystems_table)
        main_table.add_row(io_table)
        
        return main_table
    
    def get_rich_panel(self) -> Panel:
        """
        Get disk usage as a rich Panel for embedding in dashboards
        
        Returns:
            Rich Panel containing disk information
        """
        # Create layout with summary and table
        summary = self.get_summary()
        table = self.get_table()
        
        return Panel(
            table,
            title=summary,
            title_align="left",
            border_style="bright_blue",
            box=box.HEAVY,
            padding=(0, 1)
        )
    
    async def display_live(self) -> None:
        """Display disk usage with live updates"""
        with Live(self.get_table(), refresh_per_second=4, screen=True) as live:
            try:
                while True:
                    live.update(self.get_table())
                    await asyncio.sleep(self.refresh_interval)
            except KeyboardInterrupt:
                pass


def main() -> None:
    """Main function when module is run directly"""
    console = Console()
    console.print("[bold green]Disk Usage Monitor[/bold green]")
    console.print("Press Ctrl+C to exit")
    
    try:
        monitor = DiskUsage(refresh_interval=1.0)
        
        # Run the live display asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(monitor.display_live())
    except KeyboardInterrupt:
        console.print("\n[yellow]Disk Usage Monitor terminated by user[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        if os.environ.get("NETDASH_DEBUG"):
            import traceback
            console.print(traceback.format_exc())


if __name__ == "__main__":
    main()
