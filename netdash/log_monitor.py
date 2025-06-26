#!/usr/bin/env python3
"""
Log Monitor Module

Monitors system logs for security events:
- Failed login attempts
- Successful sudo usage
- SSH logins
- Authentication anomalies
"""

import os
import re
import time
import subprocess
from typing import List, Dict, Optional, Tuple, Callable
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import asyncio

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.logging import RichHandler
import logging
from rich import box

# Configure rich logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("log_monitor")

@dataclass
class LogEvent:
    """Class to store log event information"""
    timestamp: datetime
    source: str
    message: str
    level: str = "INFO"
    raw_line: str = ""
    alert: bool = False
    

@dataclass
class LogMonitorConfig:
    """Configuration for the log monitor"""
    log_file: str = "/var/log/auth.log"
    journal_unit: str = "sshd.service"
    fallback_log_file: str = ""
    max_lines: int = 100
    refresh_interval: float = 1.0
    alert_patterns: Dict[str, str] = field(default_factory=lambda: {
        "failed_login": r"authentication failure|failed password|invalid user|Failed password",
        "sudo_usage": r"sudo:.*COMMAND=",
        "ssh_login": r"sshd.*Accepted",
        "authentication": r"PAM:.*authentication",
        "suspicious_ip": r"(\b25[0-5]|\b2[0-4][0-9]|\b[01]?[0-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}"
    })


class LogMonitor:
    """Monitor and display system logs with alert detection"""
    
    def __init__(self, config: Optional[LogMonitorConfig] = None):
        """
        Initialize the log monitor
        
        Args:
            config: Optional configuration settings, defaults to standard config
        """
        self.config = config or LogMonitorConfig()
        self.console = Console()
        self.events: List[LogEvent] = []
        self._cmd_available_cache = {}  # Cache command availability
        self._initialize_log_source()
        
        # If specified log file doesn't exist and we have a fallback, use it
        if (not os.path.exists(self.config.log_file) and 
            self.config.fallback_log_file and 
            os.path.exists(self.config.fallback_log_file)):
            self.config.log_file = self.config.fallback_log_file
            
    def _initialize_log_source(self) -> None:
        """Determine the best log source based on available system commands and files"""
        # Check if the specified log file exists
        if os.path.exists(self.config.log_file) and os.access(self.config.log_file, os.R_OK):
            self.log_source = "file"
            logger.info(f"Using log file: {self.config.log_file}")
            return
            
        # Check if journalctl is available
        if self._is_command_available("journalctl"):
            self.log_source = "journalctl"
            logger.info(f"Using journalctl with unit: {self.config.journal_unit}")
            return
            
        # Check if a fallback log file was specified
        if self.config.fallback_log_file and os.path.exists(self.config.fallback_log_file):
            self.log_source = "file"
            self.config.log_file = self.config.fallback_log_file
            logger.info(f"Using fallback log file: {self.config.log_file}")
            return
            
        # If no source is available, use a dummy source
        self.log_source = "dummy"
        logger.warning("No log source available. Creating a dummy source.")
    
    def _is_command_available(self, command: str) -> bool:
        """
        Check if a command is available in the system
        
        Args:
            command: Command name to check
            
        Returns:
            True if command exists, False otherwise
        """
        if command in self._cmd_available_cache:
            return self._cmd_available_cache[command]
        
        try:
            result = subprocess.run(
                ["which", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            available = result.returncode == 0
            self._cmd_available_cache[command] = available
            return available
        except Exception:
            self._cmd_available_cache[command] = False
            return False
    
    def _run_command(self, command: List[str]) -> Tuple[bool, str]:
        """
        Run a shell command and return its output
        
        Args:
            command: List of command components
            
        Returns:
            Tuple of (success, output)
        """
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, f"Error ({result.returncode}): {result.stderr}"
        except Exception as e:
            return False, f"Exception: {str(e)}"
    
    def _tail_file(self, num_lines: int = 10) -> List[str]:
        """
        Get the last N lines from a file
        
        Args:
            num_lines: Number of lines to retrieve
            
        Returns:
            List of lines from the file
        """
        if not os.path.exists(self.config.log_file):
            return []
            
        try:
            if self._is_command_available("tail"):
                # Use the tail command if available
                success, output = self._run_command(["tail", "-n", str(num_lines), self.config.log_file])
                if success:
                    return output.splitlines()
            
            # Fallback to reading the file with Python
            with open(self.config.log_file, 'r') as f:
                return f.readlines()[-num_lines:]
                
        except Exception as e:
            logger.error(f"Error tailing file: {str(e)}")
            return []
    
    def _get_journalctl_logs(self, num_lines: int = 10) -> List[str]:
        """
        Get logs from journalctl
        
        Args:
            num_lines: Number of lines to retrieve
            
        Returns:
            List of lines from journalctl
        """
        if not self._is_command_available("journalctl"):
            return []
            
        command = ["journalctl", "-n", str(num_lines), "--no-pager"]
        
        # Add unit filter if specified
        if self.config.journal_unit:
            command.extend(["-u", self.config.journal_unit])
            
        success, output = self._run_command(command)
        if success:
            return output.splitlines()
        else:
            logger.error(f"Error getting journalctl logs: {output}")
            return []
    
    def _parse_log_line(self, line: str) -> Optional[LogEvent]:
        """
        Parse a log line into a LogEvent
        
        Args:
            line: Log line to parse
            
        Returns:
            LogEvent object or None if the line couldn't be parsed
        """
        if not line or len(line) < 10:
            return None
            
        try:
            # Try to extract timestamp with different patterns
            timestamp = None
            message = line
            source = "system"
            
            # Pattern 1: Standard syslog format (Jun 26 09:30:01)
            match = re.search(r'^([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})', line)
            if match:
                try:
                    timestamp_str = match.group(1)
                    timestamp = datetime.strptime(f"{datetime.now().year} {timestamp_str}", "%Y %b %d %H:%M:%S")
                    message = line[match.end():].strip()
                except ValueError:
                    pass
            
            # Pattern 2: ISO format timestamp (2023-06-26T09:30:01)
            if not timestamp:
                match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', line)
                if match:
                    try:
                        timestamp_str = match.group(1)
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
                        message = line[match.end():].strip()
                    except ValueError:
                        pass
            
            # Pattern 3: Another common format (2023-06-26 09:30:01)
            if not timestamp:
                match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
                if match:
                    try:
                        timestamp_str = match.group(1)
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                        message = line[match.end():].strip()
                    except ValueError:
                        pass
            
            # If we couldn't extract a timestamp, use current time
            if not timestamp:
                timestamp = datetime.now()
            
            # Try to extract the source
            source_match = re.search(r'(\w+)(\[\d+\])?: ', message)
            if source_match:
                source = source_match.group(1)
                
            # Determine if this is an alert
            alert = False
            level = "INFO"
            
            for alert_type, pattern in self.config.alert_patterns.items():
                if re.search(pattern, line, re.IGNORECASE):
                    alert = True
                    level = "WARNING" if "sudo" in alert_type else "ERROR"
                    break
            
            return LogEvent(
                timestamp=timestamp,
                source=source,
                message=message,
                level=level,
                raw_line=line,
                alert=alert
            )
            
        except Exception as e:
            logger.error(f"Error parsing log line: {str(e)}")
            return LogEvent(
                timestamp=datetime.now(),
                source="parser",
                message=f"Error parsing log: {line[:50]}...",
                level="ERROR",
                raw_line=line,
                alert=False
            )
    
    def get_recent_logs(self, num_lines: int = None) -> List[LogEvent]:
        """
        Get recent log events
        
        Args:
            num_lines: Number of lines to retrieve (default: config.max_lines)
            
        Returns:
            List of LogEvent objects
        """
        if num_lines is None:
            num_lines = self.config.max_lines
            
        raw_lines = []
        
        if self.log_source == "file":
            raw_lines = self._tail_file(num_lines)
        elif self.log_source == "journalctl":
            raw_lines = self._get_journalctl_logs(num_lines)
        elif self.log_source == "dummy":
            # Create some dummy events for testing
            timestamp = datetime.now() - timedelta(minutes=5)
            for i in range(5):
                fake_time = timestamp + timedelta(minutes=i)
                if i % 2 == 0:
                    raw_lines.append(f"{fake_time.strftime('%b %d %H:%M:%S')} sshd[123]: Accepted password for user from 192.168.1.100")
                else:
                    raw_lines.append(f"{fake_time.strftime('%b %d %H:%M:%S')} sshd[123]: Failed password for invalid user from 192.168.1.101")
        
        # Parse log lines into events
        events = []
        for line in raw_lines:
            event = self._parse_log_line(line)
            if event:
                events.append(event)
        
        return events
    
    def update(self) -> None:
        """Update the log events"""
        self.events = self.get_recent_logs()
    
    def get_alert_count(self) -> Dict[str, int]:
        """
        Count alerts by type in the current events
        
        Returns:
            Dictionary with alert counts
        """
        counts = {
            "failed_login": 0,
            "sudo_usage": 0,
            "ssh_login": 0,
            "authentication": 0,
            "suspicious_ip": 0
        }
        
        for event in self.events:
            if not event.alert:
                continue
                
            for alert_type, pattern in self.config.alert_patterns.items():
                if re.search(pattern, event.raw_line, re.IGNORECASE):
                    counts[alert_type] += 1
        
        return counts
    
    def get_formatted_logs(self, max_events: int = None) -> Text:
        """
        Format log events for display
        
        Args:
            max_events: Maximum number of events to include
            
        Returns:
            Rich Text object with formatted logs
        """
        if max_events is None:
            max_events = self.config.max_lines
            
        # Show events from newest to oldest
        sorted_events = sorted(
            self.events, 
            key=lambda e: e.timestamp if e.timestamp else datetime.now(),
            reverse=True
        )[:max_events]
        
        # Format events
        text = Text()
        for event in sorted_events:
            time_str = event.timestamp.strftime("%H:%M:%S")
            
            # Add timestamp
            text.append(f"[{time_str}] ", "bright_black")
            
            # Add source
            text.append(f"{event.source}: ", "blue")
            
            # Add message with appropriate color based on content and level
            if event.alert:
                if "failed" in event.message.lower() or "invalid" in event.message.lower():
                    text.append(f"{event.message}\n", "bold red")
                elif "sudo" in event.message.lower():
                    text.append(f"{event.message}\n", "bold yellow")
                else:
                    text.append(f"{event.message}\n", "bold magenta")
            elif event.level == "ERROR":
                text.append(f"{event.message}\n", "red")
            elif event.level == "WARNING":
                text.append(f"{event.message}\n", "yellow")
            else:
                text.append(f"{event.message}\n", "white")
                
        return text
    
    def get_panel(self, max_events: int = 10) -> Panel:
        """
        Get log events as a Rich panel for integration in dashboard
        
        Args:
            max_events: Maximum number of events to include
            
        Returns:
            Rich Panel object with formatted logs
        """
        alert_counts = self.get_alert_count()
        alert_text = " | ".join([
            f"{k.replace('_', ' ').title()}: [bold red]{v}[/bold red]" 
            for k, v in alert_counts.items() if v > 0
        ])
        
        subtitle = "Alerts: " + (alert_text or "[dim]None[/dim]")
        
        # Get the log events and format them in a more compact way
        log_content = self.get_formatted_logs(max_events)
        
        return Panel(
            log_content,
            subtitle=subtitle,
            border_style="red",
            box=box.SIMPLE
        )
    
    async def display_live(self, duration: Optional[int] = None) -> None:
        """
        Display live log monitoring in the terminal
        
        Args:
            duration: Optional duration in seconds to display logs
                     If None, will run until Ctrl+C
        """
        start_time = time.time()
        
        try:
            with Live(self.get_panel(), refresh_per_second=1/self.config.refresh_interval) as live:
                while True:
                    # Check if duration has elapsed
                    if duration and (time.time() - start_time) > duration:
                        break
                        
                    # Update logs and panel
                    self.update()
                    live.update(self.get_panel())
                    
                    # Wait for next refresh
                    await asyncio.sleep(self.config.refresh_interval)
        except KeyboardInterrupt:
            self.console.print("[yellow]Monitoring stopped by user[/yellow]")


def main(custom_log_file: str = None) -> None:
    """
    Main function to run when script is executed directly
    
    Args:
        custom_log_file: Optional path to a custom log file
    """
    console = Console()
    console.print("[bold green]Log Monitor[/bold green]")
    console.print("Press Ctrl+C to exit")
    
    # Create a custom configuration
    config = LogMonitorConfig(
        # Use custom log file if provided, otherwise default
        log_file=custom_log_file or "/var/log/auth.log",
        # Fallback to a sample log file if it exists
        fallback_log_file=str(Path.home() / "sample_auth.log"),
        # Refresh every second
        refresh_interval=1.0
    )
    
    if custom_log_file:
        console.print(f"[bold cyan]Using custom log file: {custom_log_file}[/bold cyan]")
    
    try:
        monitor = LogMonitor(config)
        
        # Run the live display asynchronously
        loop = asyncio.get_event_loop()
        loop.run_until_complete(monitor.display_live())
    except PermissionError:
        console.print("[bold red]Error: Insufficient permissions to access log files[/bold red]")
        console.print("Try running with sudo privileges")
    except FileNotFoundError:
        console.print("[bold red]Error: Specified log file not found[/bold red]")
        console.print("Please check the path and try again")
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")


if __name__ == "__main__":
    main()
