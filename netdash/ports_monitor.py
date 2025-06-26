#!/usr/bin/env python3
"""
Ports and Services Monitor Module

Displays listening ports and associated services:
- Port/protocol/service visualization
- Process information for each listening port
- Service name lookup via /etc/services
"""

import os
import sys
import time
import asyncio
import psutil
import socket
import re
from typing import Dict, List, Tuple, Optional, Any, Set
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

# Services file path
SERVICES_FILE = '/etc/services'

# Well-known service names for common ports
COMMON_SERVICES = {
    22: 'SSH', 
    80: 'HTTP', 
    443: 'HTTPS', 
    21: 'FTP',
    25: 'SMTP', 
    53: 'DNS', 
    3306: 'MySQL',
    5432: 'PostgreSQL',
    27017: 'MongoDB',
    6379: 'Redis',
    8080: 'HTTP-ALT',
    8443: 'HTTPS-ALT'
}


class PortsMonitor:
    """Monitor and display information about listening ports and services"""
    
    def __init__(self, refresh_interval: float = 1.0):
        """
        Initialize the ports monitor
        
        Args:
            refresh_interval: How often to refresh the data (in seconds)
        """
        self.refresh_interval = refresh_interval
        self.console = Console()
        self._last_update = 0
        self._listeners = []
        self._process_map = {}
        self._services_map = {}
        
        # Load service names from /etc/services
        self._load_service_names()
        
    def _load_service_names(self) -> None:
        """Load service names from /etc/services file"""
        self._services_map = {}
        
        # Start with known common services
        for port, service in COMMON_SERVICES.items():
            self._services_map[port] = service
            
        # Try to read from /etc/services
        try:
            with open(SERVICES_FILE, 'r') as f:
                for line in f:
                    # Skip comments and empty lines
                    line = line.strip()
                    if line.startswith('#') or not line:
                        continue
                    
                    # Parse service entry
                    match = re.match(r'(\S+)\s+(\d+)/(\S+)', line)
                    if match:
                        service_name, port, proto = match.groups()
                        port = int(port)
                        
                        # Store TCP and UDP services separately
                        key = (port, proto.upper())
                        self._services_map[key] = service_name
        except (FileNotFoundError, PermissionError):
            pass
            
    def _get_service_name(self, port: int, proto: str) -> str:
        """
        Get service name for a port/protocol combination
        
        Args:
            port: Port number
            proto: Protocol (TCP/UDP)
            
        Returns:
            Service name if known, otherwise empty string
        """
        # Try exact match first
        key = (port, proto.upper())
        if key in self._services_map:
            return self._services_map[key]
            
        # Try just the port
        if port in self._services_map:
            return self._services_map[port]
            
        return "unknown"
        
    def update(self) -> None:
        """Update current listening ports data"""
        # Only update if the refresh interval has passed
        current_time = time.time()
        if current_time - self._last_update >= self.refresh_interval:
            self._last_update = current_time
            
            try:
                # Get all network connections that are listening
                all_connections = psutil.net_connections(kind='inet')
                self._listeners = [conn for conn in all_connections 
                                  if conn.status == 'LISTEN']
                
                # Build a mapping of PIDs to process information
                self._process_map = {}
                for proc in psutil.process_iter(['pid', 'name', 'username', 'cmdline']):
                    try:
                        self._process_map[proc.info['pid']] = proc.info
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except (psutil.AccessDenied, PermissionError):
                # If we don't have permission, we'll show a message in the table
                self._listeners = []
                
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
        if len(cmdline) > 25:
            cmdline = cmdline[:22] + "..."
            
        return {"name": name, "username": username, "command": cmdline}
    
    def get_table(self) -> Table:
        """
        Generate a rich table with listening ports information
        
        Returns:
            Rich Table object with listening services data
        """
        self.update()
        
        # Create listening services table
        table = Table(
            box=box.SIMPLE,
            title="",
            show_header=True,
            header_style="bold green",
            show_edge=False,
            padding=(0, 1),
        )
        
        # Define columns
        table.add_column("Protocol", style="cyan", width=8)
        table.add_column("Port", justify="right", width=6)
        table.add_column("Service", width=15)
        table.add_column("Process", width=15)
        table.add_column("User", width=10)
        table.add_column("Command", width=30)
        
        # Check if we have data to display
        if not self._listeners:
            if os.geteuid() != 0:  # Not running as root
                table.add_row(
                    "N/A", "N/A", "N/A",
                    "[yellow]No data[/yellow]",
                    "N/A",
                    "[yellow]Run as root for complete port data[/yellow]"
                )
            else:
                table.add_row("N/A", "N/A", "N/A", "No listeners", "N/A", "N/A")
            return table
            
        # Sort by protocol and port
        listeners = sorted(
            self._listeners,
            key=lambda c: (c.type, c.laddr.port if c.laddr else 0)
        )
        
        # Add rows for each listening port
        for conn in listeners:
            proto = "TCP" if conn.type == 1 else "UDP" if conn.type == 2 else "UNKNOWN"
            
            # Format local port
            if conn.laddr:
                port = str(conn.laddr.port)
                
                # Get service information
                service_name = self._get_service_name(conn.laddr.port, proto)
                if service_name == "unknown":
                    service_style = "default"
                else:
                    service_style = "green"
            else:
                port = "N/A"
                service_name = "N/A"
                service_style = "default"
                
            # Get process information
            proc_info = self._get_process_info(conn.pid)
            
            # Add row to the table
            table.add_row(
                proto,
                port,
                f"[{service_style}]{service_name}[/{service_style}]",
                proc_info["name"],
                proc_info["username"],
                proc_info["command"]
            )
            
        return table
    
    def get_summary(self) -> Text:
        """
        Generate a summary of listening ports
        
        Returns:
            Rich Text object with port summary
        """
        self.update()
        
        # Count listeners by protocol
        tcp_count = sum(1 for c in self._listeners if c.type == 1)
        udp_count = sum(1 for c in self._listeners if c.type == 2)
        
        summary = Text()
        summary.append("Listening Services: ")
        summary.append(f"{len(self._listeners)} total ", "bold white")
        summary.append(f"(TCP: {tcp_count}, UDP: {udp_count})", "cyan")
        
        return summary
    
    def get_panel(self) -> Panel:
        """
        Return a panel with listening ports information
        
        Returns:
            Rich Panel with table of listening ports
        """
        table = self.get_table()
        summary = self.get_summary()
        
        panel_content = Text()
        panel_content.append(summary)
        panel_content.append("\n\n")
        panel_content.append(str(table))
        
        return Panel(
            panel_content,
            title="[bold]Listening Ports & Services[/bold]",
            border_style="cyan",
            box=box.ROUNDED
        )


async def _display_ports_info() -> None:
    """Display ports information in a live view"""
    console = Console()
    monitor = PortsMonitor(refresh_interval=1.0)
    
    with Live(console=console, screen=True, refresh_per_second=1) as live:
        try:
            while True:
                panel = monitor.get_panel()
                live.update(panel)
                await asyncio.sleep(1.0)
        except KeyboardInterrupt:
            pass


def main() -> None:
    """Run the ports monitor as a standalone component"""
    try:
        if os.geteuid() != 0:
            print("[bold yellow]WARNING: Running without root privileges. Port information may be limited.[/bold yellow]")
            print("[bold yellow]Try running with sudo for complete data.[/bold yellow]")
        
        asyncio.run(_display_ports_info())
    except KeyboardInterrupt:
        print("\nExiting Ports Monitor...")


if __name__ == "__main__":
    main()
