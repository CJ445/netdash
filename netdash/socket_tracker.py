#!/usr/bin/env python3
"""
Socket Tracker Module

Displays active network connections:
- Live TCP/UDP sockets mapped to processes
- Connection status, remote addresses and ports
- Process owner and command information
"""

import os
import sys
import time
import asyncio
import psutil
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import pwd
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

# Connection status colors
STATUS_COLORS = {
    'ESTABLISHED': 'green',
    'LISTEN': 'yellow',
    'TIME_WAIT': 'cyan',
    'CLOSE_WAIT': 'magenta',
    'FIN_WAIT1': 'red',
    'FIN_WAIT2': 'red',
    'CLOSING': 'red',
    'LAST_ACK': 'red',
    'SYN_SENT': 'blue',
    'SYN_RECV': 'blue',
    'NONE': 'white',
}


class SocketTracker:
    """Track and display active network connections"""
    
    def __init__(self, refresh_interval: float = 1.0):
        """
        Initialize the socket tracker
        
        Args:
            refresh_interval: How often to refresh the data (in seconds)
        """
        self.refresh_interval = refresh_interval
        self.console = Console()
        self._last_update = 0
        self._connections = []
        self._process_map = {}
        
    def update(self) -> None:
        """Update current socket connections data"""
        # Only update if the refresh interval has passed
        current_time = time.time()
        if current_time - self._last_update >= self.refresh_interval:
            self._last_update = current_time
            
            try:
                # Get all network connections
                self._connections = psutil.net_connections(kind='all')
                
                # Build a mapping of PIDs to process information
                self._process_map = {}
                for proc in psutil.process_iter(['pid', 'name', 'username', 'cmdline']):
                    try:
                        self._process_map[proc.info['pid']] = proc.info
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except (psutil.AccessDenied, PermissionError):
                # If we don't have permission, we'll show a message in the table
                self._connections = []
                
    def _get_process_info(self, pid: Optional[int]) -> Dict[str, str]:
        """
        Get process information for a given PID
        
        Args:
            pid: Process ID or None if not available
            
        Returns:
            Dictionary with process name, username, and command
        """
        if pid is None or pid not in self._process_map:
            return {"name": "N/A", "username": "N/A", "command": "N/A"}
        
        info = self._process_map[pid]
        name = info['name'] or "N/A"
        username = info['username'] or "N/A"
        cmdline = ' '.join(info['cmdline'] or ["N/A"])
        if len(cmdline) > 20:
            cmdline = cmdline[:17] + "..."
            
        return {"name": name, "username": username, "command": cmdline}
    
    def get_table(self) -> Table:
        """
        Generate a rich table with socket/connection information
        
        Returns:
            Rich Table object with connection data
        """
        self.update()
        
        # Create socket connections table
        table = Table(
            box=box.SIMPLE,
            title="",
            show_header=True,
            header_style="bold green",
            show_edge=False,
            padding=(0, 1),
        )
        
        # Define columns
        table.add_column("Proto", style="cyan", width=5)
        table.add_column("Local Address", width=22)
        table.add_column("Remote Address", width=22)
        table.add_column("Status", width=12)
        table.add_column("PID", width=6)
        table.add_column("Process", width=15)
        table.add_column("User", width=10)
        
        # Check if we have data to display
        if not self._connections:
            if os.geteuid() != 0:  # Not running as root
                table.add_row(
                    "N/A", "N/A", "N/A", 
                    "[yellow]No data[/yellow]", 
                    "N/A", "[yellow]Run as root for socket data[/yellow]", "N/A"
                )
            else:
                table.add_row("N/A", "N/A", "N/A", "No connections", "N/A", "N/A", "N/A")
            return table
            
        # Sort connections first by status, then by local address
        connections = sorted(
            self._connections,
            key=lambda c: (c.status if c.status else "NONE", 
                           c.laddr.port if hasattr(c.laddr, 'port') else 
                           (0 if not c.laddr else hash(str(c.laddr))))
        )
        
        # Add rows for each connection
        for conn in connections[:20]:  # Limit to first 20 connections to avoid flooding
            proto = "TCP" if conn.type == 1 else "UDP" if conn.type == 2 else "???"
            
            # Format local address
            if conn.laddr:
                local_addr = f"{conn.laddr.ip}:{conn.laddr.port}"
            else:
                local_addr = "N/A"
                
            # Format remote address
            if conn.raddr:
                remote_addr = f"{conn.raddr.ip}:{conn.raddr.port}"
            else:
                remote_addr = "*:*"
                
            # Process connection status
            status = conn.status if conn.status else "NONE"
            status_color = STATUS_COLORS.get(status, 'white')
            status_display = f"[{status_color}]{status}[/{status_color}]"
            
            # Get process information
            proc_info = self._get_process_info(conn.pid)
            
            # Add row to the table
            table.add_row(
                proto,
                local_addr,
                remote_addr,
                status_display,
                str(conn.pid) if conn.pid else "N/A",
                proc_info["name"],
                proc_info["username"]
            )
            
        return table
    
    def get_summary(self) -> Text:
        """
        Generate a summary of socket connections
        
        Returns:
            Rich Text object with connection summary
        """
        self.update()
        
        # Count connections by type and status
        tcp_count = sum(1 for c in self._connections if c.type == 1)
        udp_count = sum(1 for c in self._connections if c.type == 2)
        established = sum(1 for c in self._connections if c.status == 'ESTABLISHED')
        listening = sum(1 for c in self._connections if c.status == 'LISTEN')
        
        summary = Text()
        summary.append("Connections: ")
        summary.append(f"{len(self._connections)} total ", "bold white")
        summary.append(f"({tcp_count} TCP, {udp_count} UDP) ", "cyan")
        summary.append(f"{established} established, ", "green")
        summary.append(f"{listening} listening", "yellow")
        
        return summary
    
    def get_panel(self) -> Panel:
        """
        Return a panel with socket information
        
        Returns:
            Rich Panel with table of connections
        """
        table = self.get_table()
        summary = self.get_summary()
        
        panel_content = Text()
        panel_content.append(summary)
        panel_content.append("\n\n")
        panel_content.append(str(table))
        
        return Panel(
            panel_content,
            title="[bold]Active Network Connections[/bold]",
            border_style="blue",
            box=box.ROUNDED
        )


async def _display_socket_info() -> None:
    """Display socket information in a live view"""
    console = Console()
    tracker = SocketTracker(refresh_interval=1.0)
    
    with Live(console=console, screen=True, refresh_per_second=1) as live:
        try:
            while True:
                panel = tracker.get_panel()
                live.update(panel)
                await asyncio.sleep(1.0)
        except KeyboardInterrupt:
            pass


def main() -> None:
    """Run the socket tracker as a standalone component"""
    try:
        if os.geteuid() != 0:
            print("[bold yellow]WARNING: Running without root privileges. Socket information may be limited.[/bold yellow]")
            print("[bold yellow]Try running with sudo for complete data.[/bold yellow]")
        
        asyncio.run(_display_socket_info())
    except KeyboardInterrupt:
        print("\nExiting Socket Tracker...")


if __name__ == "__main__":
    main()
