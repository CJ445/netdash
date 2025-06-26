#!/usr/bin/env python3
"""
Security Monitor Module

Monitors security-related events:
- Failed login attempts and brute-force detection
- Sudo usage tracking and command logging
- Auth alerts and security event timeline
"""

import os
import sys
import time
import asyncio
import re
import subprocess
from typing import Dict, List, Tuple, Optional, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich import box

# Alert thresholds
FAILED_LOGIN_THRESHOLD = 5
FAILED_LOGIN_WINDOW = 300  # 5 minutes in seconds
SUDO_ALERT_WINDOW = 3600  # 1 hour in seconds


class SecurityMonitor:
    """Monitor and display security-related events"""
    
    def __init__(self, refresh_interval: float = 1.0):
        """
        Initialize the security monitor
        
        Args:
            refresh_interval: How often to refresh the data (in seconds)
        """
        self.refresh_interval = refresh_interval
        self.console = Console()
        self._last_update = 0
        
        # Recent events storage
        self._failed_logins = defaultdict(list)  # IP -> list of timestamps
        self._sudo_events = []
        self._auth_events = []
        self._security_alerts = []
        
        # Track when we last checked logs
        self._last_auth_check = 0
        self._last_sudo_check = 0
        
        # Log file paths
        self._auth_log = self._get_auth_log_path()
        self._sudo_log = self._get_sudo_log_path()
        
    def _get_auth_log_path(self) -> Optional[str]:
        """
        Determine the path to the auth log
        
        Returns:
            Path to auth log or None if not found
        """
        # Common auth log paths
        paths = [
            '/var/log/auth.log',
            '/var/log/secure',
        ]
        
        for path in paths:
            if os.path.exists(path) and os.access(path, os.R_OK):
                return path
                
        return None
    
    def _get_sudo_log_path(self) -> Optional[str]:
        """
        Determine the path to the sudo log
        
        Returns:
            Path to sudo log or None if not found
        """
        # Sudo logs are often in auth.log or secure
        return self._get_auth_log_path()
    
    def update(self) -> None:
        """Update security information"""
        # Only update if the refresh interval has passed
        current_time = time.time()
        if current_time - self._last_update >= self.refresh_interval:
            self._last_update = current_time
            
            # Update auth events
            self._update_auth_events()
            
            # Update sudo events
            self._update_sudo_events()
            
            # Clean up old events
            self._cleanup_old_events()
            
            # Check for security alerts
            self._check_for_alerts()
    
    def _update_auth_events(self) -> None:
        """Update authentication events"""
        if not self._auth_log or not os.path.exists(self._auth_log):
            return
            
        try:
            # Get file size to check if it changed
            file_size = os.path.getsize(self._auth_log)
            if self._last_auth_check == file_size:
                return
                
            # Read new lines from the auth log
            with open(self._auth_log, 'r') as f:
                # If we've read this file before, seek to near the end
                if self._last_auth_check > 0:
                    f.seek(max(0, file_size - 10000))  # Read last 10KB to catch new entries
                    f.readline()  # Skip incomplete line
                
                for line in f:
                    self._process_auth_line(line)
                    
            # Update the last check position
            self._last_auth_check = file_size
            
        except (IOError, OSError):
            pass
    
    def _process_auth_line(self, line: str) -> None:
        """
        Process a single line from the auth log
        
        Args:
            line: Log line to process
        """
        current_time = time.time()
        
        # Check for failed login attempts (SSH, PAM, etc.)
        if 'Failed password' in line or 'authentication failure' in line:
            # Try to extract IP address
            ip_match = re.search(r'from\s+(\d+\.\d+\.\d+\.\d+)', line)
            ip = ip_match.group(1) if ip_match else 'unknown'
            
            # Try to extract username
            user_match = re.search(r'user\s+(\S+)', line)
            username = user_match.group(1) if user_match else 'unknown'
            
            # Extract timestamp if possible, otherwise use current time
            timestamp_match = re.search(r'^(\w+\s+\d+\s+\d+:\d+:\d+)', line)
            if timestamp_match:
                try:
                    timestamp_str = timestamp_match.group(1)
                    # Add year since auth.log often omits it
                    current_year = datetime.now().year
                    timestamp = datetime.strptime(f'{timestamp_str} {current_year}', '%b %d %H:%M:%S %Y')
                    event_time = timestamp.timestamp()
                except ValueError:
                    event_time = current_time
            else:
                event_time = current_time
            
            # Record the failed login
            self._failed_logins[ip].append(event_time)
            
            # Add to auth events
            self._auth_events.append({
                'timestamp': event_time,
                'type': 'failed_login',
                'source_ip': ip,
                'username': username,
                'message': f"Failed login for '{username}' from {ip}"
            })
    
    def _update_sudo_events(self) -> None:
        """Update sudo usage events"""
        if not self._sudo_log or not os.path.exists(self._sudo_log):
            return
            
        try:
            # Get file size to check if it changed
            file_size = os.path.getsize(self._sudo_log)
            if self._last_sudo_check == file_size:
                return
                
            # Read new lines from the sudo log
            with open(self._sudo_log, 'r') as f:
                # If we've read this file before, seek to near the end
                if self._last_sudo_check > 0:
                    f.seek(max(0, file_size - 10000))  # Read last 10KB to catch new entries
                    f.readline()  # Skip incomplete line
                
                for line in f:
                    self._process_sudo_line(line)
                    
            # Update the last check position
            self._last_sudo_check = file_size
            
        except (IOError, OSError):
            pass
    
    def _process_sudo_line(self, line: str) -> None:
        """
        Process a single line from the sudo log
        
        Args:
            line: Log line to process
        """
        current_time = time.time()
        
        # Check for sudo command execution
        if 'sudo:' in line and 'COMMAND=' in line:
            # Extract username
            user_match = re.search(r'sudo:\s+(\S+)', line)
            username = user_match.group(1) if user_match else 'unknown'
            
            # Extract command
            cmd_match = re.search(r'COMMAND=(.+)$', line)
            command = cmd_match.group(1) if cmd_match else 'unknown'
            
            # Extract timestamp
            timestamp_match = re.search(r'^(\w+\s+\d+\s+\d+:\d+:\d+)', line)
            if timestamp_match:
                try:
                    timestamp_str = timestamp_match.group(1)
                    # Add year since auth.log often omits it
                    current_year = datetime.now().year
                    timestamp = datetime.strptime(f'{timestamp_str} {current_year}', '%b %d %H:%M:%S %Y')
                    event_time = timestamp.timestamp()
                except ValueError:
                    event_time = current_time
            else:
                event_time = current_time
            
            # Record the sudo event
            self._sudo_events.append({
                'timestamp': event_time,
                'username': username,
                'command': command,
                'message': f"User '{username}' executed sudo: {command}"
            })
    
    def _cleanup_old_events(self) -> None:
        """Clean up events older than the tracking window"""
        current_time = time.time()
        
        # Clean up failed logins
        for ip, timestamps in list(self._failed_logins.items()):
            self._failed_logins[ip] = [t for t in timestamps 
                                     if current_time - t < FAILED_LOGIN_WINDOW]
            if not self._failed_logins[ip]:
                del self._failed_logins[ip]
                
        # Clean up auth events
        cutoff_time = current_time - FAILED_LOGIN_WINDOW
        self._auth_events = [e for e in self._auth_events 
                           if e['timestamp'] > cutoff_time]
                
        # Clean up sudo events
        cutoff_time = current_time - SUDO_ALERT_WINDOW
        self._sudo_events = [e for e in self._sudo_events 
                          if e['timestamp'] > cutoff_time]
                
        # Clean up alerts
        cutoff_time = current_time - max(FAILED_LOGIN_WINDOW, SUDO_ALERT_WINDOW)
        self._security_alerts = [a for a in self._security_alerts 
                              if a['timestamp'] > cutoff_time]
    
    def _check_for_alerts(self) -> None:
        """Check for potential security alerts"""
        # Check for brute force attempts
        for ip, timestamps in self._failed_logins.items():
            if len(timestamps) >= FAILED_LOGIN_THRESHOLD:
                # Check if this is a new alert
                alert_already_exists = any(
                    a['type'] == 'brute_force' and 
                    a['source_ip'] == ip and 
                    time.time() - a['timestamp'] < 300  # Don't duplicate alerts within 5 min
                    for a in self._security_alerts
                )
                
                if not alert_already_exists:
                    self._security_alerts.append({
                        'timestamp': time.time(),
                        'type': 'brute_force',
                        'source_ip': ip,
                        'attempt_count': len(timestamps),
                        'severity': 'high',
                        'message': f"Potential brute force from {ip}: {len(timestamps)} failed logins"
                    })
        
        # Check for unusual sudo usage (many sudo commands in short time)
        if len(self._sudo_events) > 10:
            # Group by user
            sudo_by_user = defaultdict(list)
            for event in self._sudo_events:
                sudo_by_user[event['username']].append(event['timestamp'])
                
            # Check for users with many sudo commands
            for username, timestamps in sudo_by_user.items():
                # If more than 10 sudo commands in 5 minutes
                recent_timestamps = [t for t in timestamps 
                                   if time.time() - t < 300]
                                   
                if len(recent_timestamps) >= 10:
                    # Check if this is a new alert
                    alert_already_exists = any(
                        a['type'] == 'sudo_abuse' and 
                        a['username'] == username and 
                        time.time() - a['timestamp'] < 300  # Don't duplicate alerts within 5 min
                        for a in self._security_alerts
                    )
                    
                    if not alert_already_exists:
                        self._security_alerts.append({
                            'timestamp': time.time(),
                            'type': 'sudo_abuse',
                            'username': username,
                            'command_count': len(recent_timestamps),
                            'severity': 'medium',
                            'message': f"Unusual sudo activity by {username}: {len(recent_timestamps)} commands in 5 min"
                        })
    
    def _format_timestamp(self, timestamp: float) -> str:
        """
        Format a timestamp in a human-readable format
        
        Args:
            timestamp: Unix timestamp
            
        Returns:
            Formatted timestamp string
        """
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    
    def get_login_attempts_table(self) -> Table:
        """
        Generate a table with recent failed login attempts
        
        Returns:
            Rich Table with failed login data
        """
        self.update()
        
        # Create table
        table = Table(
            box=box.SIMPLE,
            title="",
            show_header=True,
            header_style="bold red",
            show_edge=False,
            padding=(0, 1),
        )
        
        # Define columns
        table.add_column("Time", width=19)
        table.add_column("Source IP", width=15)
        table.add_column("Username", width=12)
        table.add_column("Status", width=8)
        
        # Filter auth events for failed logins
        failed_logins = [e for e in self._auth_events 
                       if e['type'] == 'failed_login']
        
        # Sort by timestamp (most recent first)
        failed_logins.sort(key=lambda e: e['timestamp'], reverse=True)
        
        # Add rows
        if not failed_logins:
            table.add_row("N/A", "N/A", "N/A", "No failed logins")
        else:
            for event in failed_logins[:10]:  # Show last 10
                timestamp = self._format_timestamp(event['timestamp'])
                ip = event.get('source_ip', 'unknown')
                
                # Color IP red if it's a potential brute force
                ip_style = "red" if len(self._failed_logins.get(ip, [])) >= FAILED_LOGIN_THRESHOLD else "default"
                
                table.add_row(
                    timestamp,
                    f"[{ip_style}]{ip}[/{ip_style}]",
                    event.get('username', 'unknown'),
                    "[red]FAILED[/red]"
                )
                
        return table
    
    def get_sudo_logs_table(self) -> Table:
        """
        Generate a table with recent sudo command executions
        
        Returns:
            Rich Table with sudo usage data
        """
        self.update()
        
        # Create table
        table = Table(
            box=box.SIMPLE,
            title="",
            show_header=True,
            header_style="bold yellow",
            show_edge=False,
            padding=(0, 1),
        )
        
        # Define columns
        table.add_column("Time", width=19)
        table.add_column("User", width=12)
        table.add_column("Command", width=40)
        
        # Sort by timestamp (most recent first)
        sudo_events = sorted(self._sudo_events, key=lambda e: e['timestamp'], reverse=True)
        
        # Add rows
        if not sudo_events:
            table.add_row("N/A", "N/A", "No sudo commands detected")
        else:
            for event in sudo_events[:10]:  # Show last 10
                timestamp = self._format_timestamp(event['timestamp'])
                command = event.get('command', 'unknown')
                
                # Truncate command if too long
                if len(command) > 40:
                    command = command[:37] + "..."
                
                table.add_row(
                    timestamp,
                    event.get('username', 'unknown'),
                    command
                )
                
        return table
    
    def get_alerts_table(self) -> Table:
        """
        Generate a table with security alerts
        
        Returns:
            Rich Table with security alerts
        """
        self.update()
        
        # Create table
        table = Table(
            box=box.SIMPLE,
            title="",
            show_header=True,
            header_style="bold white on red",
            show_edge=False,
            padding=(0, 1),
        )
        
        # Define columns
        table.add_column("Time", width=19)
        table.add_column("Type", width=15)
        table.add_column("Severity", width=8)
        table.add_column("Details", width=40)
        
        # Sort by timestamp (most recent first) and severity
        def alert_sort_key(alert):
            # Sort by severity first (high > medium > low)
            severity_value = {'high': 0, 'medium': 1, 'low': 2}.get(alert.get('severity', 'low'), 3)
            # Then by timestamp (most recent first)
            return (severity_value, -alert['timestamp'])
            
        alerts = sorted(self._security_alerts, key=alert_sort_key)
        
        # Add rows
        if not alerts:
            table.add_row("N/A", "N/A", "N/A", "No active security alerts")
        else:
            for alert in alerts[:10]:  # Show top 10
                timestamp = self._format_timestamp(alert['timestamp'])
                
                # Format alert type
                alert_type = alert.get('type', 'unknown')
                formatted_type = alert_type.replace('_', ' ').title()
                
                # Format severity with color
                severity = alert.get('severity', 'low')
                if severity == 'high':
                    severity_text = "[bold red]HIGH[/bold red]"
                elif severity == 'medium':
                    severity_text = "[yellow]MEDIUM[/yellow]"
                else:
                    severity_text = "[green]LOW[/green]"
                
                table.add_row(
                    timestamp,
                    formatted_type,
                    severity_text,
                    alert.get('message', 'Unknown alert')
                )
                
        return table
    
    def get_summary(self) -> Text:
        """
        Generate a summary of security status
        
        Returns:
            Rich Text object with security summary
        """
        self.update()
        
        # Count issues
        failed_login_count = len(self._auth_events)
        sudo_count = len(self._sudo_events)
        alert_count = len(self._security_alerts)
        
        # Count high severity alerts
        high_severity_count = sum(1 for a in self._security_alerts 
                              if a.get('severity') == 'high')
        
        summary = Text()
        summary.append("Security Status: ")
        
        if high_severity_count > 0:
            summary.append("ALERT ", "bold white on red")
        elif alert_count > 0:
            summary.append("WARNING ", "yellow")
        else:
            summary.append("OK ", "green")
            
        summary.append(f"{alert_count} alerts ", "red" if alert_count > 0 else "green")
        summary.append(f"{failed_login_count} failed logins ", "red" if failed_login_count > 5 else "yellow" if failed_login_count > 0 else "green")
        summary.append(f"{sudo_count} privilege escalations", "yellow" if sudo_count > 10 else "green")
        
        return summary
    
    def get_panel(self) -> Panel:
        """
        Return a panel with security information
        
        Returns:
            Rich Panel with security tables
        """
        alerts_table = self.get_alerts_table()
        login_table = self.get_login_attempts_table()
        sudo_table = self.get_sudo_logs_table()
        summary = self.get_summary()
        
        panel_content = Text()
        panel_content.append(summary)
        
        # Add security alerts
        panel_content.append("\n\n")
        panel_content.append(Rule("Security Alerts", style="red"))
        panel_content.append("\n")
        panel_content.append(str(alerts_table))
        
        # Add failed login attempts
        panel_content.append("\n\n")
        panel_content.append(Rule("Failed Login Attempts", style="yellow"))
        panel_content.append("\n")
        panel_content.append(str(login_table))
        
        # Add sudo logs
        panel_content.append("\n\n")
        panel_content.append(Rule("Sudo Command History", style="blue"))
        panel_content.append("\n")
        panel_content.append(str(sudo_table))
        
        # Show message if no auth log access
        if not self._auth_log or not os.access(self._auth_log, os.R_OK):
            panel_content.append("\n\n")
            panel_content.append("[bold yellow]NOTE: Cannot access system auth logs. Run with sudo for complete data.[/bold yellow]")
        
        return Panel(
            panel_content,
            title="[bold]Security Monitor[/bold]",
            border_style="red",
            box=box.ROUNDED
        )


async def _display_security_info() -> None:
    """Display security information in a live view"""
    console = Console()
    monitor = SecurityMonitor(refresh_interval=1.0)
    
    with Live(console=console, screen=True, refresh_per_second=1) as live:
        try:
            while True:
                panel = monitor.get_panel()
                live.update(panel)
                await asyncio.sleep(1.0)
        except KeyboardInterrupt:
            pass


def main() -> None:
    """Run the security monitor as a standalone component"""
    try:
        if os.geteuid() != 0:
            print("[bold yellow]WARNING: Running without root privileges. Security monitoring may be limited.[/bold yellow]")
            print("[bold yellow]Try running with sudo for complete data.[/bold yellow]")
        
        asyncio.run(_display_security_info())
    except KeyboardInterrupt:
        print("\nExiting Security Monitor...")


if __name__ == "__main__":
    main()
