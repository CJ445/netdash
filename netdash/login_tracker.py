#!/usr/bin/env python3
"""
Login Tracker Module

Displays information about current logins and recent login history:
- Currently logged-in users (similar to 'who')
- Recent login history (similar to 'last')
"""

import os
import pwd
import subprocess
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

@dataclass
class UserLogin:
    """Class to store user login information"""
    username: str
    tty: str
    host: str = ""
    login_time: Optional[datetime] = None
    logout_time: Optional[datetime] = None
    is_active: bool = True


class LoginTracker:
    """Track and display user login information"""
    
    def __init__(self):
        """Initialize the login tracker"""
        self.console = Console()
        self._cmd_available_cache = {}  # Cache command availability
    
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
    
    def _parse_who_output(self, output: str) -> List[UserLogin]:
        """
        Parse the output of the 'who' command
        
        Args:
            output: Output string from 'who' command
            
        Returns:
            List of UserLogin objects
        """
        logins = []
        
        for line in output.strip().split('\n'):
            if not line.strip():
                continue
                
            parts = line.split()
            if len(parts) < 5:
                continue
                
            username = parts[0]
            tty = parts[1]
            
            # Try to parse the date and time
            date_str = ' '.join(parts[2:5])
            login_time = None
            try:
                # Format like: 2023-06-26 09:30:00
                login_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    # Format like: Jun 26 09:30
                    login_time = datetime.strptime(f"{datetime.now().year} {date_str}", "%Y %b %d %H:%M")
                except ValueError:
                    pass
            
            # Extract the host/IP if available
            host = ""
            if len(parts) >= 6 and '(' in parts[5] and ')' in parts[5]:
                host = parts[5].strip('()')
            
            logins.append(UserLogin(
                username=username,
                tty=tty,
                host=host,
                login_time=login_time,
                is_active=True
            ))
                
        return logins
    
    def _parse_last_output(self, output: str, max_entries: int = 5) -> List[UserLogin]:
        """
        Parse the output of the 'last' command
        
        Args:
            output: Output string from 'last' command
            max_entries: Maximum number of entries to return
            
        Returns:
            List of UserLogin objects
        """
        logins = []
        
        for line in output.strip().split('\n')[:max_entries]:
            if not line.strip() or "wtmp begins" in line:
                continue
                
            parts = line.split()
            if len(parts) < 5:
                continue
                
            username = parts[0]
            tty = parts[1]
            
            # Extract host if available
            host = ""
            if len(parts) >= 3 and parts[2] != ":" and parts[2] != "system" and ":" not in parts[2]:
                host = parts[2]
            
            # Try to parse the login date and time
            try:
                # Find the index where date starts (typically after tty and possibly host)
                date_start_idx = 2 if not host else 3
                date_str = ' '.join(parts[date_start_idx:date_start_idx+5])
                login_time = datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y")
            except (ValueError, IndexError):
                login_time = None
            
            # Parse logout time if available
            logout_time = None
            is_active = False
            if " still logged in" in line:
                is_active = True
            else:
                try:
                    # Try to find the logout time after "- "
                    logout_idx = line.find(" - ")
                    if logout_idx != -1:
                        logout_part = line[logout_idx + 3:].strip().split('(')[0].strip()
                        if "gone" not in logout_part and "crash" not in logout_part:
                            logout_time_parts = logout_part.split()
                            if len(logout_time_parts) >= 2:
                                logout_time = datetime.strptime(
                                    f"{datetime.now().year} {logout_time_parts[0]} {logout_time_parts[1]}", 
                                    "%Y %b %d %H:%M"
                                )
                except (ValueError, IndexError):
                    pass
            
            logins.append(UserLogin(
                username=username,
                tty=tty,
                host=host,
                login_time=login_time,
                logout_time=logout_time,
                is_active=is_active
            ))
        
        return logins
    
    def get_active_logins(self) -> List[UserLogin]:
        """
        Get a list of currently active user logins
        
        Returns:
            List of UserLogin objects
        """
        if self._is_command_available("who"):
            success, output = self._run_command(["who"])
            if success:
                return self._parse_who_output(output)
        
        # Fallback: Try to get login info from system files
        try:
            active_logins = []
            for user_info in pwd.getpwall():
                if user_info.pw_shell and not user_info.pw_shell.endswith("nologin"):
                    # This user might be able to login
                    active_logins.append(UserLogin(
                        username=user_info.pw_name,
                        tty="system",
                        is_active=False  # We can't confirm activity this way
                    ))
            return active_logins
        except Exception:
            return []
    
    def get_login_history(self, max_entries: int = 5) -> List[UserLogin]:
        """
        Get recent login history
        
        Args:
            max_entries: Maximum number of entries to retrieve
            
        Returns:
            List of UserLogin objects
        """
        if self._is_command_available("last"):
            success, output = self._run_command(["last", "-n", str(max_entries)])
            if success:
                return self._parse_last_output(output, max_entries)
        
        return []
    
    def get_active_logins_table(self) -> Table:
        """
        Generate a rich Table with currently active login sessions
        
        Returns:
            Rich Table object with active logins
        """
        table = Table(box=box.SIMPLE)
        
        # Add columns
        table.add_column("Username", style="cyan bold")
        table.add_column("TTY", style="green")
        table.add_column("Host", style="yellow")
        table.add_column("Login Time", style="blue")
        
        # Get active logins and add rows
        logins = self.get_active_logins()
        if logins:
            for login in logins:
                login_time_str = login.login_time.strftime("%Y-%m-%d %H:%M") if login.login_time else "Unknown"
                table.add_row(
                    login.username,
                    login.tty,
                    login.host or "local",
                    login_time_str
                )
        else:
            table.add_row("[dim]No active logins found[/dim]", "", "", "")
        
        return table
    
    def get_login_history_table(self, max_entries: int = 5) -> Table:
        """
        Generate a rich Table with recent login history
        
        Args:
            max_entries: Maximum number of entries to show
            
        Returns:
            Rich Table object with login history
        """
        table = Table(box=box.SIMPLE)
        
        # Add columns
        table.add_column("Username", style="cyan bold")
        table.add_column("TTY", style="green")
        table.add_column("Host", style="yellow")
        table.add_column("Login Time", style="blue")
        table.add_column("Status", style="magenta")
        
        # Get login history and add rows
        logins = self.get_login_history(max_entries)
        if logins:
            for login in logins:
                login_time_str = login.login_time.strftime("%Y-%m-%d %H:%M") if login.login_time else "Unknown"
                
                if login.is_active:
                    status = "[bold green]Active[/bold green]"
                elif login.logout_time:
                    logout_time_str = login.logout_time.strftime("%H:%M")
                    status = f"Logout at {logout_time_str}"
                else:
                    status = "Session ended"
                
                table.add_row(
                    login.username,
                    login.tty,
                    login.host or "local",
                    login_time_str,
                    status
                )
        else:
            table.add_row("[dim]No login history found[/dim]", "", "", "", "")
        
        return table
    
    def display(self) -> None:
        """Display login information in the terminal"""
        active_logins_table = self.get_active_logins_table()
        history_table = self.get_login_history_table()
        
        self.console.print(active_logins_table)
        self.console.print("")
        self.console.print(history_table)
    
    def get_panels(self) -> List[Panel]:
        """
        Get login information as Rich panels for integration in dashboard
        
        Returns:
            List of Rich panels
        """
        return [
            Panel(self.get_active_logins_table(), title="Active Logins"),
            Panel(self.get_login_history_table(), title="Login History")
        ]


def main() -> None:
    """Main function to run when script is executed directly"""
    console = Console()
    console.print("[bold green]Login Tracker[/bold green]")
    
    try:
        tracker = LoginTracker()
        tracker.display()
    except PermissionError:
        console.print("[bold red]Error: Insufficient permissions to access login information[/bold red]")
        console.print("Try running with sudo privileges")
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")


if __name__ == "__main__":
    main()
