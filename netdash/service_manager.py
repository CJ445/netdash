#!/usr/bin/env python3
"""
Service Manager Module

Displays and controls system services (systemd):
- Filterable service status (active/failed)
- Quick controls to start/stop/restart services
- Service logs and error monitoring
"""

import os
import sys
import time
import asyncio
import subprocess
from typing import Dict, List, Tuple, Optional, Any, Set
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.prompt import Prompt

# Maximum services to display at once
MAX_DISPLAY_SERVICES = 30

# Service status colors
STATUS_COLORS = {
    'active': 'green',
    'running': 'green',
    'exited': 'cyan',
    'inactive': 'grey70',
    'failed': 'red',
    'dead': 'red',
    'unknown': 'yellow',
}


class ServiceManager:
    """Monitor and control system services (systemd)"""
    
    def __init__(self, refresh_interval: float = 2.0, filter_str: str = ''):
        """
        Initialize the service manager
        
        Args:
            refresh_interval: How often to refresh the data (in seconds)
            filter_str: Initial filter string for services
        """
        self.refresh_interval = refresh_interval
        self.console = Console()
        self._last_update = 0
        self._services = []
        self._filter_str = filter_str
        self._has_systemctl = self._check_systemctl()
        self._selected_service = None
        
    def _check_systemctl(self) -> bool:
        """
        Check if systemctl is available
        
        Returns:
            True if systemctl is available, False otherwise
        """
        try:
            subprocess.run(['systemctl', '--version'], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE,
                          check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def update(self) -> None:
        """Update service status information"""
        # Only update if systemctl is available and refresh interval has passed
        current_time = time.time()
        if not self._has_systemctl or current_time - self._last_update < self.refresh_interval:
            return
            
        self._last_update = current_time
        
        try:
            # Get all services with their status
            cmd = ['systemctl', 'list-units', '--type=service', '--all', '--no-pager', '--plain']
            output = subprocess.check_output(cmd, text=True)
            
            # Parse the output
            self._services = []
            for line in output.strip().split('\n'):
                if not line or 'UNIT' in line or 'LOAD' in line:
                    continue
                
                parts = line.split(None, 4)
                if len(parts) >= 4:
                    unit_name = parts[0]
                    load_state = parts[1]
                    active_state = parts[2]
                    sub_state = parts[3]
                    description = parts[4] if len(parts) > 4 else ""
                    
                    # Only include .service units
                    if unit_name.endswith('.service'):
                        name = unit_name.replace('.service', '')
                        
                        # Apply filter if set
                        if not self._filter_str or self._filter_str.lower() in name.lower() or self._filter_str.lower() in description.lower():
                            self._services.append({
                                'name': name,
                                'unit': unit_name,
                                'load': load_state,
                                'active': active_state,
                                'status': sub_state,
                                'description': description
                            })
                            
            # Sort by status (failed first, then active, then inactive)
            def sort_key(service):
                if service['status'] == 'failed':
                    return 0
                if service['active'] == 'active':
                    return 1
                return 2
                
            self._services.sort(key=sort_key)
            
        except (subprocess.CalledProcessError, FileNotFoundError, PermissionError):
            self._services = []
    
    def set_filter(self, filter_str: str) -> None:
        """
        Set a filter string for services
        
        Args:
            filter_str: String to filter services by
        """
        self._filter_str = filter_str
        self._last_update = 0  # Force an update
        
    def service_action(self, service_name: str, action: str) -> Tuple[bool, str]:
        """
        Perform an action on a service
        
        Args:
            service_name: Name of the service
            action: Action to perform (start, stop, restart, status)
            
        Returns:
            Tuple of (success, message)
        """
        if not self._has_systemctl:
            return False, "systemctl not available"
            
        if not service_name.endswith('.service'):
            service_name += '.service'
            
        valid_actions = {'start', 'stop', 'restart', 'status'}
        if action not in valid_actions:
            return False, f"Invalid action: {action}"
            
        try:
            cmd = ['systemctl', action, service_name]
            if os.geteuid() != 0 and action != 'status':
                cmd = ['sudo'] + cmd
                
            result = subprocess.run(cmd,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  text=True)
            
            if result.returncode == 0:
                message = f"Service {service_name} {action} successful"
                if action == 'status' and result.stdout:
                    message = result.stdout
                return True, message
            else:
                return False, result.stderr or f"Failed to {action} {service_name}"
                
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            return False, str(e)
    
    def get_service_logs(self, service_name: str, lines: int = 10) -> str:
        """
        Get recent logs for a service
        
        Args:
            service_name: Name of the service
            lines: Number of log lines to get
            
        Returns:
            String with recent logs
        """
        if not self._has_systemctl:
            return "systemctl not available"
            
        if not service_name.endswith('.service'):
            service_name += '.service'
            
        try:
            cmd = ['journalctl', '-u', service_name, '--no-pager', '-n', str(lines)]
            result = subprocess.run(cmd,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 text=True)
            
            if result.returncode == 0 and result.stdout:
                return result.stdout
            else:
                return result.stderr or "No logs available"
                
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            return str(e)
    
    def select_service(self, index: int) -> Optional[Dict[str, str]]:
        """
        Select a service by index
        
        Args:
            index: Index of the service in the current filtered list
            
        Returns:
            Service dict if valid index, None otherwise
        """
        if 0 <= index < len(self._services):
            self._selected_service = self._services[index]
            return self._selected_service
        return None
    
    def get_selected_service(self) -> Optional[Dict[str, str]]:
        """
        Get the currently selected service
        
        Returns:
            Selected service dict or None
        """
        return self._selected_service
    
    def get_table(self, include_index: bool = False) -> Table:
        """
        Generate a rich table with service information
        
        Args:
            include_index: Whether to include an index column
            
        Returns:
            Rich Table object with service data
        """
        self.update()
        
        # Create services table
        table = Table(
            box=box.SIMPLE,
            title="",
            show_header=True,
            header_style="bold green",
            show_edge=False,
            padding=(0, 1),
        )
        
        # Define columns
        if include_index:
            table.add_column("#", justify="right", style="dim", width=3)
        table.add_column("Service", style="cyan", width=20)
        table.add_column("Status", width=10)
        table.add_column("Description", width=40)
        
        # Check if systemctl is available
        if not self._has_systemctl:
            table.add_row(
                "N/A" if include_index else None,
                "[yellow]systemctl not available[/yellow]",
                "N/A",
                "Install systemd or run on a systemd-based system"
            )
            return table
            
        # Check if we have data to display
        if not self._services:
            if os.geteuid() != 0:
                table.add_row(
                    "N/A" if include_index else None,
                    "[yellow]Limited access[/yellow]",
                    "N/A",
                    "Run as root for complete service data"
                )
            else:
                table.add_row(
                    "N/A" if include_index else None,
                    "No matching services",
                    "N/A",
                    "Try a different filter" if self._filter_str else "No services found"
                )
            return table
            
        # Add rows for services (limit to avoid flooding)
        for i, service in enumerate(self._services[:MAX_DISPLAY_SERVICES]):
            status = service['status'] or "unknown"
            status_color = STATUS_COLORS.get(status.lower(), "white")
            
            # Highlight the selected service
            if self._selected_service and service['name'] == self._selected_service['name']:
                name_style = "reverse cyan"
            else:
                name_style = "cyan"
                
            # Add row with optional index
            if include_index:
                table.add_row(
                    str(i),
                    f"[{name_style}]{service['name']}[/{name_style}]",
                    f"[{status_color}]{status}[/{status_color}]",
                    service['description']
                )
            else:
                table.add_row(
                    f"[{name_style}]{service['name']}[/{name_style}]",
                    f"[{status_color}]{status}[/{status_color}]",
                    service['description']
                )
            
        # If we truncated the list, add a note
        if len(self._services) > MAX_DISPLAY_SERVICES:
            remaining = len(self._services) - MAX_DISPLAY_SERVICES
            if include_index:
                table.add_row(
                    "...",
                    f"[dim]+{remaining} more[/dim]",
                    "",
                    f"[dim]Use filter to see more specific results[/dim]"
                )
            else:
                table.add_row(
                    f"[dim]+{remaining} more[/dim]",
                    "",
                    f"[dim]Use filter to see more specific results[/dim]"
                )
            
        return table
    
    def get_summary(self) -> Text:
        """
        Generate a summary of service status
        
        Returns:
            Rich Text object with service summary
        """
        self.update()
        
        # Count services by status
        total = len(self._services)
        active = sum(1 for s in self._services if s['active'] == 'active')
        failed = sum(1 for s in self._services if s['status'] == 'failed')
        
        summary = Text()
        summary.append("Services: ")
        if self._filter_str:
            summary.append(f"Filter: '{self._filter_str}' ", "bold")
            
        summary.append(f"{total} total ", "white")
        summary.append(f"{active} active ", "green")
        
        if failed > 0:
            summary.append(f"{failed} failed", "red")
        
        return summary
    
    def get_control_panel(self) -> Panel:
        """
        Generate a panel with service controls
        
        Returns:
            Panel with service control options
        """
        selected = self.get_selected_service()
        
        content = Text()
        if selected:
            content.append(f"Selected: [bold cyan]{selected['name']}[/bold cyan]\n")
            content.append(f"Status: [{STATUS_COLORS.get(selected['status'].lower(), 'white')}]{selected['status']}[/{STATUS_COLORS.get(selected['status'].lower(), 'white')}]\n\n")
            
            content.append("[bold]Controls:[/bold]\n")
            content.append("[s] Start   [t] Stop   [r] Restart   [l] View Logs\n")
            content.append("[↑/↓] Navigate   [/] Filter   [q] Quit\n")
        else:
            content.append("[yellow]No service selected[/yellow]\n\n")
            content.append("[bold]Controls:[/bold]\n")
            content.append("[↑/↓] Navigate   [Enter] Select   [/] Filter   [q] Quit\n")
            
        return Panel(
            content,
            title="[bold]Service Controls[/bold]",
            border_style="blue",
            box=box.ROUNDED
        )
    
    def get_panel(self) -> Panel:
        """
        Return a panel with service information
        
        Returns:
            Rich Panel with table of services and controls
        """
        table = self.get_table(include_index=True)
        summary = self.get_summary()
        controls = self.get_control_panel()
        
        # Combine components
        content = Text()
        content.append(summary)
        content.append("\n\n")
        content.append(str(table))
        content.append("\n\n")
        content.append(str(controls))
        
        return Panel(
            content,
            title="[bold]Service Manager[/bold]",
            border_style="yellow",
            box=box.ROUNDED
        )


async def _interactive_service_manager() -> None:
    """Run an interactive service manager session"""
    from rich.prompt import Prompt
    import termios
    import tty
    import sys
    import fcntl
    import os
    import asyncio
    import subprocess
    
    console = Console()
    manager = ServiceManager(refresh_interval=2.0)
    selected_idx = 0
    
    def getch():
        """Get a single character from stdin"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch
    
    with Live(console=console, screen=True, refresh_per_second=1) as live:
        try:
            while True:
                # Get updated panel
                panel = manager.get_panel()
                live.update(panel)
                
                # Make stdin non-blocking
                fd = sys.stdin.fileno()
                fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
                
                # Check for keypresses for a short time
                for _ in range(5):  # Check for 0.5 seconds
                    try:
                        key = sys.stdin.read(1)
                        if key:
                            break
                    except (IOError, OSError):
                        key = None
                    await asyncio.sleep(0.1)
                
                # Restore blocking mode
                fcntl.fcntl(fd, fcntl.F_SETFL, fl)
                
                # If no key was pressed, continue to the next update
                if not key:
                    await asyncio.sleep(1.5)
                    continue
                
                # Process the key
                if key == 'q':
                    break
                    
                # Arrow keys navigation
                elif key == '\x1b':  # Escape sequence, likely arrow key
                    # Read the next two characters
                    sys.stdin.read(1)  # Skip '['
                    arrow = sys.stdin.read(1)
                    
                    # Move selection up/down
                    if arrow == 'A':  # Up arrow
                        selected_idx = max(0, selected_idx - 1)
                    elif arrow == 'B':  # Down arrow
                        selected_idx = min(len(manager._services) - 1, selected_idx + 1)
                        
                    # Select the service
                    if 0 <= selected_idx < len(manager._services):
                        manager.select_service(selected_idx)
                        
                # Enter to select
                elif key == '\r':
                    if 0 <= selected_idx < len(manager._services):
                        manager.select_service(selected_idx)
                        
                # Filter
                elif key == '/':
                    # Clear the screen
                    console.print("\033[2J\033[H")
                    filter_str = Prompt.ask("Filter services")
                    manager.set_filter(filter_str)
                    selected_idx = 0
                    
                # Service controls
                elif key == 's':  # Start
                    selected = manager.get_selected_service()
                    if selected:
                        success, message = manager.service_action(selected['name'], 'start')
                        console.print(f"\n{message}")
                        await asyncio.sleep(1.5)
                        
                elif key == 't':  # Stop
                    selected = manager.get_selected_service()
                    if selected:
                        success, message = manager.service_action(selected['name'], 'stop')
                        console.print(f"\n{message}")
                        await asyncio.sleep(1.5)
                        
                elif key == 'r':  # Restart
                    selected = manager.get_selected_service()
                    if selected:
                        success, message = manager.service_action(selected['name'], 'restart')
                        console.print(f"\n{message}")
                        await asyncio.sleep(1.5)
                        
                elif key == 'l':  # View logs
                    selected = manager.get_selected_service()
                    if selected:
                        # Clear the screen and show logs
                        console.print("\033[2J\033[H")
                        logs = manager.get_service_logs(selected['name'], 20)
                        console.print(f"[bold]Logs for {selected['name']}:[/bold]\n")
                        console.print(logs)
                        console.print("\n[bold]Press any key to return[/bold]")
                        getch()  # Wait for keypress
                
                # Force a refresh
                manager._last_update = 0
                await asyncio.sleep(0.1)
                        
        except KeyboardInterrupt:
            pass


def main() -> None:
    """Run the service manager as a standalone component"""
    try:
        if os.geteuid() != 0:
            print("[bold yellow]WARNING: Running without root privileges. Some service operations may be limited.[/bold yellow]")
            print("[bold yellow]Try running with sudo for full control.[/bold yellow]")
        
        asyncio.run(_interactive_service_manager())
    except KeyboardInterrupt:
        print("\nExiting Service Manager...")


if __name__ == "__main__":
    main()
