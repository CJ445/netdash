#!/usr/bin/env python3
"""
Network Statistics Monitor Module

Displays real-time network interface statistics including:
- Bytes sent/received
- Packets sent/received
- Current bandwidth usage
"""

import time
import psutil
from typing import Dict, Optional, Tuple, List
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich import box

class NetworkStats:
    """Network statistics collector and formatter"""
    
    def __init__(self, refresh_interval: float = 1.0):
        """
        Initialize the network stats monitor
        
        Args:
            refresh_interval: Time between updates in seconds
        """
        self.refresh_interval = refresh_interval
        self.console = Console()
        self.previous_counters = None
        self.current_counters = None
        self._include_loopback = False  # Initialize the attribute
        self._get_counters()  # Initialize counters
    
    def _get_counters(self) -> None:
        """Get network counters for all interfaces"""
        self.previous_counters = self.current_counters
        self.current_counters = psutil.net_io_counters(pernic=True)
    
    def _calculate_speed(self, interface: str) -> Tuple[float, float]:
        """
        Calculate upload and download speed for an interface
        
        Args:
            interface: Network interface name
        
        Returns:
            Tuple of (upload_speed, download_speed) in bytes/second
        """
        if not self.previous_counters or interface not in self.previous_counters:
            return 0.0, 0.0
        
        current = self.current_counters[interface]
        previous = self.previous_counters[interface]
        
        # Calculate bytes sent/received per second
        bytes_sent = current.bytes_sent - previous.bytes_sent
        bytes_recv = current.bytes_recv - previous.bytes_recv
        
        upload_speed = bytes_sent / self.refresh_interval
        download_speed = bytes_recv / self.refresh_interval
        
        return upload_speed, download_speed
    
    def _format_bytes(self, num_bytes: float) -> str:
        """
        Format bytes into human-readable format
        
        Args:
            num_bytes: Number of bytes
            
        Returns:
            Human-readable string (e.g., "1.23 MB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(num_bytes) < 1024.0:
                return f"{num_bytes:.2f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:.2f} PB"
    
    def _get_interface_data(self) -> List[Dict]:
        """
        Get formatted data for all network interfaces
        
        Returns:
            List of dictionaries containing interface data
        """
        self._get_counters()
        result = []
        
        for interface, counters in self.current_counters.items():
            # Skip loopback interface by default
            if interface == 'lo' and not self._include_loopback:
                continue
                
            upload_speed, download_speed = self._calculate_speed(interface)
            
            result.append({
                'interface': interface,
                'bytes_sent': counters.bytes_sent,
                'bytes_recv': counters.bytes_recv,
                'packets_sent': counters.packets_sent,
                'packets_recv': counters.packets_recv,
                'upload_speed': upload_speed,
                'download_speed': download_speed,
                'upload_speed_fmt': self._format_bytes(upload_speed),
                'download_speed_fmt': self._format_bytes(download_speed),
                'bytes_sent_fmt': self._format_bytes(counters.bytes_sent),
                'bytes_recv_fmt': self._format_bytes(counters.bytes_recv)
            })
        
        return result
    
    def get_table(self) -> Table:
        """
        Generate a rich Table with current network stats
        
        Returns:
            Rich Table object with network statistics
        """
        table = Table(box=box.SIMPLE)
        
        # Add columns
        table.add_column("Interface", style="cyan bold")
        table.add_column("TX\n(Total)", style="green", justify="right")
        table.add_column("RX\n(Total)", style="green", justify="right")
        table.add_column("TX Speed", style="yellow", justify="right")
        table.add_column("RX Speed", style="yellow", justify="right")
        table.add_column("Packets\nSent", style="blue", justify="right")
        table.add_column("Packets\nReceived", style="blue", justify="right")
        
        # Get interface data and add rows
        interfaces = self._get_interface_data()
        for iface in interfaces:
            table.add_row(
                iface['interface'],
                iface['bytes_sent_fmt'],
                iface['bytes_recv_fmt'],
                iface['upload_speed_fmt'] + '/s',
                iface['download_speed_fmt'] + '/s',
                str(iface['packets_sent']),
                str(iface['packets_recv'])
            )
        
        return table
    
    def display_live(self, duration: Optional[int] = None) -> None:
        """
        Display live network statistics in the terminal
        
        Args:
            duration: Optional duration in seconds to display stats
                     If None, will run until Ctrl+C
        """
        self._include_loopback = True  # Show loopback in standalone mode
        
        start_time = time.time()
        with Live(self.get_table(), refresh_per_second=1/self.refresh_interval) as live:
            try:
                while True:
                    # Check if duration has elapsed
                    if duration and (time.time() - start_time) > duration:
                        break
                        
                    # Update the table
                    time.sleep(self.refresh_interval)
                    live.update(self.get_table())
            except KeyboardInterrupt:
                self.console.print("[yellow]Monitoring stopped by user[/yellow]")
    
    def get_raw_data(self) -> List[Dict]:
        """
        Get raw network data for use in other components
        
        Returns:
            List of dictionaries with interface data
        """
        self._include_loopback = False  # Don't include loopback by default for API
        return self._get_interface_data()


def main() -> None:
    """Main function to run when script is executed directly"""
    console = Console()
    console.print("[bold green]Network Statistics Monitor[/bold green]")
    console.print("Press Ctrl+C to exit")
    
    try:
        monitor = NetworkStats(refresh_interval=1.0)
        monitor.display_live()
    except PermissionError:
        console.print("[bold red]Error: Insufficient permissions to access network information[/bold red]")
        console.print("Try running with sudo privileges")
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")


if __name__ == "__main__":
    main()
