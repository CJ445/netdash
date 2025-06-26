#!/usr/bin/env python3
"""
Memory Usage Monitor Module

Displays detailed memory usage information:
- RAM usage breakdown (used, cached, free)
- Swap usage and pressure
- Color-coded indicators for memory pressure
"""

import os
import sys
import time
import asyncio
import psutil
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import BarColumn, Progress, TextColumn
from rich import box

# Color thresholds for memory utilization
LOW_THRESHOLD = 50
MEDIUM_THRESHOLD = 75
HIGH_THRESHOLD = 90


class MemoryMonitor:
    """Monitor and display memory usage information"""
    
    def __init__(self, refresh_interval: float = 1.0):
        """
        Initialize the memory monitor
        
        Args:
            refresh_interval: How often to refresh the data (in seconds)
        """
        self.refresh_interval = refresh_interval
        self.console = Console()
        self._last_update = 0
        self._memory_stats = {}
        self._swap_stats = {}
        self.update()
    
    def update(self) -> None:
        """Update memory statistics"""
        current_time = time.time()
        
        # Only update if refresh interval has elapsed
        if current_time - self._last_update >= self.refresh_interval:
            # Get memory info
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Store memory stats
            self._memory_stats = {
                'total': mem.total,
                'available': mem.available,
                'used': mem.used,
                'free': mem.free,
                'percent': mem.percent,
                'cached': getattr(mem, 'cached', 0),
                'buffers': getattr(mem, 'buffers', 0),
                'shared': getattr(mem, 'shared', 0)
            }
            
            # Store swap stats
            self._swap_stats = {
                'total': swap.total,
                'used': swap.used,
                'free': swap.free,
                'percent': swap.percent,
                'sin': getattr(swap, 'sin', 0),
                'sout': getattr(swap, 'sout', 0)
            }
            
            self._last_update = current_time
    
    def _get_color_for_percentage(self, percent: float) -> str:
        """
        Get the color based on the percentage value
        
        Args:
            percent: Memory utilization percentage
            
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
        value = bytes_value
        
        while value >= 1024 and unit_index < len(units) - 1:
            value /= 1024
            unit_index += 1
        
        return f"{value:.1f} {units[unit_index]}"
    
    def get_summary(self) -> Text:
        """
        Get a summary of memory information
        
        Returns:
            Rich Text object with memory summary
        """
        self.update()
        
        text = Text()
        
        # Total memory
        total_gb = self._memory_stats['total'] / (1024 * 1024 * 1024)
        text.append(f"Total RAM: {total_gb:.1f} GB\n")
        
        # Current usage percentage
        percent = self._memory_stats['percent']
        color = self._get_color_for_percentage(percent)
        text.append("Memory Usage: ")
        text.append(f"{percent:.1f}%", style=f"bold {color}")
        
        # Add swap info if available
        if self._swap_stats['total'] > 0:
            text.append("\n")
            swap_percent = self._swap_stats['percent']
            swap_color = self._get_color_for_percentage(swap_percent)
            text.append("Swap Usage: ")
            text.append(f"{swap_percent:.1f}%", style=f"bold {swap_color}")
        
        return text
    
    def get_table(self) -> Table:
        """
        Get a table of memory usage with bars
        
        Returns:
            Rich Table object with memory usage
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
        table.add_column("Memory Type", style="cyan")
        table.add_column("Size", justify="right", style="green")
        table.add_column("Usage %", justify="right", width=8)
        table.add_column("Usage", ratio=1)
        
        # Memory usage bar
        mem_percent = self._memory_stats['percent']
        mem_color = self._get_color_for_percentage(mem_percent)
        
        # Create bar for memory usage
        bar_width = 30  # Fixed width for the bar
        filled = int(mem_percent / 100 * bar_width)
        mem_bar = "█" * filled + "░" * (bar_width - filled)
        
        # Add memory rows
        table.add_row(
            "RAM",
            self._format_bytes(self._memory_stats['total']),
            f"{mem_percent:.1f}%",
            Text(mem_bar, style=mem_color)
        )
        
        # Format specific memory components
        used_without_cache = self._memory_stats['used'] - self._memory_stats.get('cached', 0) - self._memory_stats.get('buffers', 0)
        used_percent = (used_without_cache / self._memory_stats['total']) * 100 if self._memory_stats['total'] > 0 else 0
        
        # App Memory (Used - Cached - Buffers)
        filled = int(used_percent / 100 * bar_width)
        used_bar = "█" * filled + "░" * (bar_width - filled)
        used_color = self._get_color_for_percentage(used_percent)
        
        table.add_row(
            "├─ Applications",
            self._format_bytes(used_without_cache),
            f"{used_percent:.1f}%",
            Text(used_bar, style=used_color)
        )
        
        # Cached memory
        if self._memory_stats.get('cached', 0) > 0:
            cached = self._memory_stats['cached']
            cached_percent = (cached / self._memory_stats['total']) * 100 if self._memory_stats['total'] > 0 else 0
            filled = int(cached_percent / 100 * bar_width)
            cached_bar = "█" * filled + "░" * (bar_width - filled)
            
            table.add_row(
                "├─ Cached",
                self._format_bytes(cached),
                f"{cached_percent:.1f}%",
                Text(cached_bar, style="cyan")
            )
        
        # Buffers memory
        if self._memory_stats.get('buffers', 0) > 0:
            buffers = self._memory_stats['buffers']
            buffers_percent = (buffers / self._memory_stats['total']) * 100 if self._memory_stats['total'] > 0 else 0
            filled = int(buffers_percent / 100 * bar_width)
            buffers_bar = "█" * filled + "░" * (bar_width - filled)
            
            table.add_row(
                "├─ Buffers",
                self._format_bytes(buffers),
                f"{buffers_percent:.1f}%",
                Text(buffers_bar, style="blue")
            )
        
        # Free memory
        free = self._memory_stats['free']
        free_percent = (free / self._memory_stats['total']) * 100 if self._memory_stats['total'] > 0 else 0
        filled = int(free_percent / 100 * bar_width)
        free_bar = "█" * filled + "░" * (bar_width - filled)
        
        table.add_row(
            "└─ Free",
            self._format_bytes(free),
            f"{free_percent:.1f}%",
            Text(free_bar, style="green")
        )
        
        # Add swap if available
        if self._swap_stats['total'] > 0:
            swap_percent = self._swap_stats['percent']
            swap_color = self._get_color_for_percentage(swap_percent)
            
            # Create bar for swap usage
            filled = int(swap_percent / 100 * bar_width)
            swap_bar = "█" * filled + "░" * (bar_width - filled)
            
            table.add_section()
            table.add_row(
                "SWAP",
                self._format_bytes(self._swap_stats['total']),
                f"{swap_percent:.1f}%",
                Text(swap_bar, style=swap_color)
            )
            
            # Add swap details
            if self._swap_stats['sin'] > 0 or self._swap_stats['sout'] > 0:
                swap_pressure = "Low"
                pressure_color = "green"
                
                if self._swap_stats['sin'] > 10485760 or self._swap_stats['sout'] > 10485760:  # 10MB
                    swap_pressure = "Medium"
                    pressure_color = "yellow"
                    
                if self._swap_stats['sin'] > 52428800 or self._swap_stats['sout'] > 52428800:  # 50MB
                    swap_pressure = "High"
                    pressure_color = "red"
                
                table.add_row(
                    "└─ Pressure",
                    f"Sin: {self._format_bytes(self._swap_stats['sin'])}, Sout: {self._format_bytes(self._swap_stats['sout'])}",
                    "",
                    Text(swap_pressure, style=pressure_color)
                )
        
        return table
    
    def get_rich_panel(self) -> Panel:
        """
        Get memory usage as a rich Panel for embedding in dashboards
        
        Returns:
            Rich Panel containing memory information
        """
        # Create layout with summary and table
        summary = self.get_summary()
        table = self.get_table()
        
        return Panel(
            table,
            title=summary,
            title_align="left",
            border_style="bright_magenta",
            box=box.HEAVY,
            padding=(0, 1)
        )
    
    async def display_live(self) -> None:
        """Display memory usage with live updates"""
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
    console.print("[bold green]Memory Monitor[/bold green]")
    console.print("Press Ctrl+C to exit")
    
    try:
        monitor = MemoryMonitor(refresh_interval=1.0)
        
        # Run the live display asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(monitor.display_live())
    except KeyboardInterrupt:
        console.print("\n[yellow]Memory Monitor terminated by user[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        if os.environ.get("NETDASH_DEBUG"):
            import traceback
            console.print(traceback.format_exc())


if __name__ == "__main__":
    main()
