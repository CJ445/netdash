#!/usr/bin/env python3
"""
Container Monitor Module

Displays information about Docker/LXD containers:
- Running container list and resource usage
- Container status, images, and health information 
- Container resource usage (CPU, memory, network, IO)
"""

import os
import sys
import time
import asyncio
import subprocess
import json
from typing import Dict, List, Tuple, Optional, Any, Set
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import BarColumn, Progress, TextColumn
from rich import box

# Container status colors
STATUS_COLORS = {
    'running': 'green',
    'created': 'blue',
    'restarting': 'yellow',
    'exited': 'red',
    'paused': 'cyan',
    'dead': 'red',
    'healthy': 'green',
    'unhealthy': 'red',
    'starting': 'yellow',
    'stopping': 'yellow',
    'unknown': 'white',
}

# Container type icons
CONTAINER_ICONS = {
    'docker': '🐳',
    'lxd': '📦',
    'podman': '🎮',
    'kubernetes': '☸️',
}


class ContainerMonitor:
    """Monitor and display container resource usage and status"""
    
    def __init__(self, refresh_interval: float = 2.0):
        """
        Initialize the container monitor
        
        Args:
            refresh_interval: How often to refresh the data (in seconds)
        """
        self.refresh_interval = refresh_interval
        self.console = Console()
        self._last_update = 0
        self._containers = []
        self._has_docker = self._check_command('docker')
        self._has_lxc = self._check_command('lxc')
        self._container_stats = {}
        
    def _check_command(self, cmd: str) -> bool:
        """
        Check if a command is available
        
        Args:
            cmd: Command to check
            
        Returns:
            True if available, False otherwise
        """
        try:
            subprocess.run([cmd, '--version'], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def update(self) -> None:
        """Update container information"""
        # Only update if the refresh interval has passed
        current_time = time.time()
        if current_time - self._last_update >= self.refresh_interval:
            self._last_update = current_time
            
            # Reset containers list
            self._containers = []
            
            # Check Docker containers
            if self._has_docker:
                self._update_docker_containers()
                
            # Check LXD containers
            if self._has_lxc:
                self._update_lxc_containers()
    
    def _update_docker_containers(self) -> None:
        """Update Docker container information"""
        try:
            # Get container list
            cmd = ['docker', 'ps', '--all', '--format', '{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.RunningFor}}|{{.Ports}}']
            output = subprocess.check_output(cmd, text=True)
            
            for line in output.strip().split('\n'):
                if not line:
                    continue
                    
                parts = line.split('|')
                if len(parts) >= 4:
                    container_id = parts[0]
                    name = parts[1]
                    image = parts[2]
                    status_str = parts[3]
                    running_for = parts[4] if len(parts) > 4 else ""
                    ports = parts[5] if len(parts) > 5 else ""
                    
                    # Parse status
                    status = "unknown"
                    if "Up" in status_str:
                        status = "running"
                    elif "Exited" in status_str:
                        status = "exited"
                    elif "Created" in status_str:
                        status = "created"
                    elif "Restarting" in status_str:
                        status = "restarting"
                    elif "Paused" in status_str:
                        status = "paused"
                    
                    # Get container stats if running
                    stats = None
                    if status == "running":
                        stats = self._get_docker_stats(container_id)
                    
                    container = {
                        'id': container_id,
                        'name': name,
                        'type': 'docker',
                        'image': image,
                        'status': status,
                        'running_for': running_for,
                        'ports': ports,
                        'stats': stats
                    }
                    
                    self._containers.append(container)
                    
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    
    def _get_docker_stats(self, container_id: str) -> Optional[Dict[str, Any]]:
        """
        Get stats for a Docker container
        
        Args:
            container_id: Docker container ID
            
        Returns:
            Dictionary with container stats or None
        """
        try:
            # Get container stats in JSON format
            cmd = ['docker', 'stats', container_id, '--no-stream', '--format', '{{json .}}']
            output = subprocess.check_output(cmd, text=True)
            
            # Parse JSON stats
            stats = json.loads(output)
            
            # Extract key metrics
            return {
                'cpu': stats.get('CPUPerc', 'N/A'),
                'memory': stats.get('MemUsage', 'N/A'),
                'memory_perc': stats.get('MemPerc', 'N/A'),
                'network': stats.get('NetIO', 'N/A'),
                'block_io': stats.get('BlockIO', 'N/A')
            }
            
        except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError):
            return None
    
    def _update_lxc_containers(self) -> None:
        """Update LXC container information"""
        try:
            # Get container list with basic info
            cmd = ['lxc', 'list', '--format=json']
            output = subprocess.check_output(cmd, text=True)
            
            # Parse JSON output
            containers = json.loads(output)
            
            for container in containers:
                # Extract container information
                container_name = container.get('name', 'unknown')
                status = container.get('status', 'unknown').lower()
                
                # Get container info
                try:
                    info_cmd = ['lxc', 'info', container_name, '--format=json']
                    info_output = subprocess.check_output(info_cmd, text=True)
                    info = json.loads(info_output)
                    
                    # Extract image info
                    config = info.get('config', {})
                    image = config.get('image.description', 'N/A')
                    
                    # Extract resource usage if running
                    stats = None
                    if status == "running":
                        state = info.get('state', {})
                        memory = state.get('memory', {})
                        network = state.get('network', {})
                        
                        # Create stats object
                        stats = {
                            'cpu': f"{state.get('cpu', {}).get('usage', 0)}%",
                            'memory': f"{memory.get('usage', 0) / (1024 * 1024):.1f}MB",
                            'memory_perc': f"{memory.get('usage', 0) / max(1, memory.get('total', 1)) * 100:.1f}%",
                            'network': "N/A",
                            'block_io': "N/A"
                        }
                        
                        # Try to get network stats
                        if network:
                            total_rx = 0
                            total_tx = 0
                            for iface, iface_stats in network.items():
                                if iface != 'lo':
                                    counters = iface_stats.get('counters', {})
                                    total_rx += counters.get('bytes_received', 0)
                                    total_tx += counters.get('bytes_sent', 0)
                            
                            stats['network'] = f"{total_rx / (1024 * 1024):.1f}MB / {total_tx / (1024 * 1024):.1f}MB"
                    
                    container = {
                        'id': container_name,
                        'name': container_name,
                        'type': 'lxd',
                        'image': image,
                        'status': status,
                        'running_for': 'N/A',
                        'ports': 'N/A',
                        'stats': stats
                    }
                    
                    self._containers.append(container)
                    
                except (subprocess.SubprocessError, json.JSONDecodeError):
                    pass
                
        except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError):
            pass
    
    def get_table(self) -> Table:
        """
        Generate a rich table with container information
        
        Returns:
            Rich Table object with container data
        """
        self.update()
        
        # Create container table
        table = Table(
            box=box.SIMPLE,
            title="",
            show_header=True,
            header_style="bold green",
            show_edge=False,
            padding=(0, 1),
        )
        
        # Define columns
        table.add_column("Type", width=6)
        table.add_column("Name", style="cyan", width=20)
        table.add_column("Status", width=10)
        table.add_column("Image", width=20)
        table.add_column("CPU", width=8)
        table.add_column("Memory", width=12)
        table.add_column("Network I/O", width=14)
        
        # Check if we have data to display
        if not self._containers:
            if not self._has_docker and not self._has_lxc:
                table.add_row(
                    "N/A", 
                    "[yellow]No container runtime detected[/yellow]", 
                    "N/A", 
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A"
                )
            else:
                table.add_row(
                    "N/A",
                    "No containers found",
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A"
                )
            return table
            
        # Sort containers by status (running first)
        sorted_containers = sorted(
            self._containers, 
            key=lambda c: (0 if c['status'] == 'running' else 1, c['name'])
        )
        
        # Add rows for each container
        for container in sorted_containers:
            # Get container icon
            icon = CONTAINER_ICONS.get(container['type'], '?')
            
            # Get status with color
            status = container['status']
            status_color = STATUS_COLORS.get(status, 'white')
            status_display = f"[{status_color}]{status}[/{status_color}]"
            
            # Get stats if available
            cpu = "N/A"
            memory = "N/A"
            network = "N/A"
            
            if container['stats']:
                cpu = container['stats'].get('cpu', 'N/A')
                memory = container['stats'].get('memory', 'N/A')
                network = container['stats'].get('network', 'N/A')
                
            # Add row
            table.add_row(
                f"{icon} {container['type']}",
                container['name'],
                status_display,
                container['image'],
                cpu,
                memory,
                network
            )
            
        return table
    
    def get_summary(self) -> Text:
        """
        Generate a summary of container status
        
        Returns:
            Rich Text object with container summary
        """
        self.update()
        
        # Count containers by type and status
        total = len(self._containers)
        running = sum(1 for c in self._containers if c['status'] == 'running')
        docker_count = sum(1 for c in self._containers if c['type'] == 'docker')
        lxd_count = sum(1 for c in self._containers if c['type'] == 'lxd')
        
        summary = Text()
        summary.append("Containers: ")
        summary.append(f"{total} total ", "bold white")
        summary.append(f"({running} running) ", "green")
        
        if docker_count > 0:
            summary.append(f"Docker: {docker_count} ", "blue")
            
        if lxd_count > 0:
            summary.append(f"LXD: {lxd_count}", "cyan")
            
        return summary
    
    def get_panel(self) -> Panel:
        """
        Return a panel with container information
        
        Returns:
            Rich Panel with table of containers
        """
        table = self.get_table()
        summary = self.get_summary()
        
        panel_content = Text()
        panel_content.append(summary)
        panel_content.append("\n\n")
        panel_content.append(str(table))
        
        return Panel(
            panel_content,
            title="[bold]Container Monitor[/bold]",
            border_style="green",
            box=box.ROUNDED
        )


async def _display_container_info() -> None:
    """Display container information in a live view"""
    console = Console()
    monitor = ContainerMonitor(refresh_interval=2.0)
    
    with Live(console=console, screen=True, refresh_per_second=0.5) as live:
        try:
            while True:
                panel = monitor.get_panel()
                live.update(panel)
                await asyncio.sleep(2.0)
        except KeyboardInterrupt:
            pass


def main() -> None:
    """Run the container monitor as a standalone component"""
    try:
        if os.geteuid() != 0:
            print("[bold yellow]WARNING: Running without root privileges. Container information may be limited.[/bold yellow]")
        
        asyncio.run(_display_container_info())
    except KeyboardInterrupt:
        print("\nExiting Container Monitor...")


if __name__ == "__main__":
    main()
