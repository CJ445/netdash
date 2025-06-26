#!/usr/bin/env python3
"""
CPU Monitor Module

Monitors CPU usage and load averages:
- Per-core CPU utilization with color-coded bars
- System load averages (1, 5, 15 min)
- Core temperature (if available)
"""

import os
import sys
import time
import asyncio
import psutil
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import platform
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import BarColumn, Progress, TextColumn
from rich import box

# Color thresholds for CPU utilization and load
LOW_THRESHOLD = 30
MEDIUM_THRESHOLD = 70
HIGH_THRESHOLD = 90


class CPUMonitor:
    """Monitor and display CPU usage and load information"""
    
    def __init__(self, refresh_interval: float = 1.0):
        """
        Initialize the CPU monitor
        
        Args:
            refresh_interval: How often to refresh the data (in seconds)
        """
        self.refresh_interval = refresh_interval
        self.console = Console()
        self._cpu_count = psutil.cpu_count(logical=True)
        self._cpu_count_physical = psutil.cpu_count(logical=False)
        self._last_update = 0
        self._last_cpu_percent = [0.0] * self._cpu_count if self._cpu_count else []
        self._last_load_avg = (0.0, 0.0, 0.0)
        self._cpu_freq = {'current': 0, 'min': 0, 'max': 0}
        self.update()
    
    def update(self) -> None:
        """Update CPU statistics"""
        current_time = time.time()
        
        # Only update if refresh interval has elapsed
        if current_time - self._last_update >= self.refresh_interval:
            # Get per-CPU usage percentages
            self._last_cpu_percent = psutil.cpu_percent(percpu=True)
            
            # Get load averages (Linux/macOS only)
            try:
                self._last_load_avg = os.getloadavg()
            except (AttributeError, OSError):
                # Windows or other OS without getloadavg
                self._last_load_avg = (0.0, 0.0, 0.0)
            
            # Get CPU frequency if available
            try:
                self._cpu_freq = psutil.cpu_freq()._asdict()
            except Exception:
                self._cpu_freq = {'current': 0, 'min': 0, 'max': 0}
                
            self._last_update = current_time
    
    def _get_color_for_percentage(self, percent: float) -> str:
        """
        Get the color based on the percentage value
        
        Args:
            percent: CPU utilization percentage
            
        Returns:
            Color string for rich
        """
        if percent < LOW_THRESHOLD:
            return "green"
        elif percent < MEDIUM_THRESHOLD:
            return "yellow"
        elif percent < HIGH_THRESHOLD:
            return "dark_orange"
        else:
            return "red"
    
    def _get_color_for_load(self, load: float, core_count: int) -> str:
        """
        Get color for load average based on core count
        
        Args:
            load: Load average value
            core_count: Number of CPU cores
            
        Returns:
            Color string for rich
        """
        # Calculate load per core
        load_per_core = load / core_count if core_count > 0 else 0
        
        if load_per_core < 0.7:  # Less than 70% load per core
            return "green"
        elif load_per_core < 1.0:  # Less than 100% load per core
            return "yellow"
        elif load_per_core < 1.5:  # Less than 150% load per core
            return "dark_orange"
        else:  # More than 150% load per core
            return "red"
    
    def get_summary(self) -> Text:
        """
        Get a summary of CPU information
        
        Returns:
            Rich Text object with CPU summary
        """
        self.update()
        
        text = Text()
        text.append(f"CPU: {platform.processor()}\n")
        text.append(f"Cores: {self._cpu_count_physical} Physical, {self._cpu_count} Logical\n")
        
        if self._cpu_freq['current'] > 0:
            current_ghz = self._cpu_freq['current'] / 1000 if self._cpu_freq['current'] > 1000 else self._cpu_freq['current']
            text.append(f"Frequency: {current_ghz:.2f} GHz")
            
            if self._cpu_freq['max'] > 0:
                max_ghz = self._cpu_freq['max'] / 1000 if self._cpu_freq['max'] > 1000 else self._cpu_freq['max']
                text.append(f" (Max: {max_ghz:.2f} GHz)")
            
            text.append("\n")
        
        # System load averages
        if any(x > 0 for x in self._last_load_avg):
            text.append("Load Average: ")
            
            # 1 minute load
            color = self._get_color_for_load(self._last_load_avg[0], self._cpu_count_physical)
            text.append(f"{self._last_load_avg[0]:.2f}", style=f"bold {color}")
            
            # 5 minute load
            text.append(", ")
            color = self._get_color_for_load(self._last_load_avg[1], self._cpu_count_physical)
            text.append(f"{self._last_load_avg[1]:.2f}", style=f"bold {color}")
            
            # 15 minute load
            text.append(", ")
            color = self._get_color_for_load(self._last_load_avg[2], self._cpu_count_physical)
            text.append(f"{self._last_load_avg[2]:.2f}", style=f"bold {color}")
            
            text.append(" (1, 5, 15 min)")
        
        return text
    
    def get_table(self) -> Table:
        """
        Get a table of CPU usage with bars
        
        Returns:
            Rich Table object with CPU usage
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
        table.add_column("Core", justify="right", style="cyan", width=6)
        table.add_column("Usage %", justify="right", width=8)
        table.add_column("Usage", ratio=1)
        
        # Add rows for each CPU core
        for i, percent in enumerate(self._last_cpu_percent):
            color = self._get_color_for_percentage(percent)
            
            # Create bar for CPU usage
            bar_width = 50  # Fixed width for the bar
            filled = int(percent / 100 * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)
            
            table.add_row(
                f"CPU {i}",
                f"{percent:.1f}%",
                Text(bar, style=color)
            )
        
        # Add system-wide average if we have cores
        if self._last_cpu_percent:
            avg = sum(self._last_cpu_percent) / len(self._last_cpu_percent)
            color = self._get_color_for_percentage(avg)
            
            # Create bar for average CPU usage
            bar_width = 50  # Fixed width for the bar
            filled = int(avg / 100 * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)
            
            table.add_section()
            table.add_row(
                "AVG",
                f"{avg:.1f}%",
                Text(bar, style=color)
            )
        
        return table
    
    async def display_live(self) -> None:
        """Display CPU usage with live updates"""
        with Live(self.get_table(), refresh_per_second=4, screen=True) as live:
            try:
                while True:
                    live.update(self.get_table())
                    await asyncio.sleep(self.refresh_interval)
            except KeyboardInterrupt:
                pass
    
    def get_rich_panel(self) -> Panel:
        """
        Get CPU usage as a rich Panel for embedding in dashboards
        
        Returns:
            Rich Panel containing CPU information
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


def main() -> None:
    """Main function when module is run directly"""
    console = Console()
    console.print("[bold green]CPU Monitor[/bold green]")
    console.print("Press Ctrl+C to exit")
    
    try:
        monitor = CPUMonitor(refresh_interval=1.0)
        
        # Run the live display asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(monitor.display_live())
    except KeyboardInterrupt:
        console.print("\n[yellow]CPU Monitor terminated by user[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        if os.environ.get("NETDASH_DEBUG"):
            import traceback
            console.print(traceback.format_exc())


if __name__ == "__main__":
    main()
