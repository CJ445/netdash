#!/usr/bin/env python3
"""
NetDash - Main Entry Point

A modular Linux terminal tool for network monitoring,
user login tracking, and log-based alerts
"""

import os
import sys
import argparse
from rich.console import Console

# Try to import Textual, but fall back to Rich-only if it's not available
try:
    from textual.app import App
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

from netdash.dashboard import main as run_dashboard


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="NetDash - Network Monitoring Dashboard"
    )
    
    parser.add_argument(
        "--rich-only", 
        action="store_true",
        help="Use Rich-based dashboard instead of Textual"
    )
    
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug mode"
    )
    
    parser.add_argument(
        "--no-color", 
        action="store_true",
        help="Disable colored output"
    )
    
    parser.add_argument(
        "--component", 
        choices=["cpu", "memory", "network", "login", "log", "disk", "socket", 
                "ports", "system", "service", "container", "vm", "security"],
        help="Run only a specific component"
    )
    
    parser.add_argument(
        "--log-file",
        type=str,
        help="Path to a custom log file to monitor"
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the application"""
    console = Console()
    args = parse_arguments()
    
    # Set environment variables based on arguments
    if args.debug:
        os.environ["NETDASH_DEBUG"] = "1"
    
    if args.no_color:
        os.environ["NO_COLOR"] = "1"
    
    # If a specific component is requested, run only that
    if args.component:
        if args.component == "cpu":
            console.print("[bold green]Running CPU Monitor component[/bold green]")
            from netdash.cpu_monitor import main as run_cpu
            run_cpu()
        elif args.component == "memory":
            console.print("[bold green]Running Memory Monitor component[/bold green]")
            from netdash.memory_monitor import main as run_memory
            run_memory()
        elif args.component == "network":
            console.print("[bold green]Running Network Statistics component[/bold green]")
            from netdash.network_stats import main as run_network
            run_network()
        elif args.component == "login":
            console.print("[bold green]Running Login Tracker component[/bold green]")
            from netdash.login_tracker import main as run_login
            run_login()
        elif args.component == "log":
            console.print("[bold green]Running Log Monitor component[/bold green]")
            from netdash.log_monitor import main as run_log
            if args.log_file:
                run_log(args.log_file)
            else:
                run_log()
        elif args.component == "disk":
            console.print("[bold green]Running Disk Usage Monitor component[/bold green]")
            from netdash.disk_usage import main as run_disk
            run_disk()
        elif args.component == "socket":
            console.print("[bold green]Running Socket Tracker component[/bold green]")
            from netdash.socket_tracker import main as run_socket
            run_socket()
        elif args.component == "ports":
            console.print("[bold green]Running Ports Monitor component[/bold green]")
            from netdash.ports_monitor import main as run_ports
            run_ports()
        elif args.component == "system":
            console.print("[bold green]Running System Health Monitor component[/bold green]")
            from netdash.system_health import main as run_system
            run_system()
        elif args.component == "service":
            console.print("[bold green]Running Service Manager component[/bold green]")
            from netdash.service_manager import main as run_service
            run_service()
        elif args.component == "container":
            console.print("[bold green]Running Container Monitor component[/bold green]")
            from netdash.container_monitor import main as run_container
            run_container()
        elif args.component == "vm":
            console.print("[bold green]Running VM Monitor component[/bold green]")
            from netdash.vm_monitor import main as run_vm
            run_vm()
        elif args.component == "security":
            console.print("[bold green]Running Security Monitor component[/bold green]")
            from netdash.security_monitor import main as run_security
            run_security()
    
    # Run the full dashboard
    use_textual = TEXTUAL_AVAILABLE and not args.rich_only
    
    if not TEXTUAL_AVAILABLE and not args.rich_only:
        console.print("[yellow]Textual library not found. Falling back to Rich-only dashboard.[/yellow]")
        console.print("[yellow]Install Textual for the full experience: pip install textual[/yellow]")
        use_textual = False
    
    try:
        run_dashboard(use_textual, args.log_file)
    except KeyboardInterrupt:
        console.print("\n[yellow]NetDash terminated by user[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error running NetDash: {str(e)}[/bold red]")
        if args.debug:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
