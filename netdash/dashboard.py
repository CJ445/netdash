#!/usr/bin/env python3
"""
Network Dashboard (NetDash)

A modular TUI dashboard for:
- Real-time network statistics
- User login monitoring
- System log monitoring with alerts
"""

import os
import sys
import time
import asyncio
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich import box
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static

# Import the individual components
from netdash.network_stats import NetworkStats
from netdash.login_tracker import LoginTracker
from netdash.log_monitor import LogMonitor, LogMonitorConfig
from netdash.cpu_monitor import CPUMonitor
from netdash.memory_monitor import MemoryMonitor
from netdash.disk_usage import DiskUsage
from netdash.socket_tracker import SocketTracker
from netdash.ports_monitor import PortsMonitor
from netdash.system_health import SystemHealth
from netdash.service_manager import ServiceManager
from netdash.container_monitor import ContainerMonitor
from netdash.vm_monitor import VMMonitor
from netdash.security_monitor import SecurityMonitor
from netdash.disk_usage import DiskUsage

# Get current folder for potential relative logging
HOME_DIR = os.path.expanduser("~")


class DashboardPanel(Static):
    """Base panel for dashboard components"""
    
    def __init__(self, title: str, component, panel_id: str):
        """
        Initialize a dashboard panel
        
        Args:
            title: Panel title
            component: Component to display in panel
            panel_id: CSS ID for the panel
        """
        super().__init__(id=panel_id)
        self.title = title
        self.component = component
        self.border_style = "blue"
    
    def compose(self) -> ComposeResult:
        """Compose the panel with title and content area"""
        yield Static(self.title, classes="panel-title")
        yield Static("Loading...", classes="panel-content", id=f"{self.id}-content")
    
    async def update_content(self):
        """Update panel content - to be implemented by subclasses"""
        pass


class NetworkPanel(DashboardPanel):
    """Panel for network statistics"""
    
    def __init__(self):
        """Initialize network panel"""
        self.net_stats = NetworkStats(refresh_interval=1.0)
        super().__init__("NETWORK STATISTICS", self.net_stats, "network-panel")
    
    async def update_content(self):
        """Update network statistics"""
        table = self.net_stats.get_table()
        content = self.query_one(f"#{self.id}-content", Static)
        content.update(table)


class LoginPanel(DashboardPanel):
    """Panel for login tracking"""
    
    def __init__(self):
        """Initialize login panel"""
        self.login_tracker = LoginTracker()
        super().__init__("USER LOGIN INFORMATION", self.login_tracker, "login-panel")
    
    async def update_content(self):
        """Update login information"""
        active_table = self.login_tracker.get_active_logins_table()
        history_table = self.login_tracker.get_login_history_table()
        
        # Combine the tables in a vertical layout
        layout = Layout()
        layout.split_column(
            Layout(active_table, name="active", ratio=1),
            Layout(history_table, name="history", ratio=1)
        )
        
        content = self.query_one(f"#{self.id}-content", Static)
        content.update(layout)


class LogPanel(DashboardPanel):
    """Panel for log monitoring"""
    
    def __init__(self):
        """Initialize log panel"""
        # Get custom log file from environment if set
        custom_log_file = os.environ.get("NETDASH_LOG_FILE")
        
        # Create a custom configuration
        config = LogMonitorConfig(
            # Use custom log file if provided, otherwise default
            log_file=custom_log_file or "/var/log/auth.log",
            # Fallback to a sample log file if it exists
            fallback_log_file=os.path.join(HOME_DIR, "sample_auth.log"),
            # Refresh every second
            refresh_interval=1.0
        )
        
        self.log_monitor = LogMonitor(config)
        super().__init__("SECURITY LOG MONITOR", self.log_monitor, "log-panel")
    
    async def update_content(self):
        """Update log information"""
        self.log_monitor.update()
        panel = self.log_monitor.get_panel()
        content = self.query_one(f"#{self.id}-content", Static)
        content.update(panel)


class CPUPanel(DashboardPanel):
    """Panel for CPU monitoring"""
    
    def __init__(self):
        """Initialize CPU panel"""
        self.cpu_monitor = CPUMonitor(refresh_interval=1.0)
        super().__init__("CPU USAGE & LOAD", self.cpu_monitor, "cpu-panel")
    
    async def update_content(self):
        """Update CPU statistics"""
        table = self.cpu_monitor.get_table()
        summary = self.cpu_monitor.get_summary()
        
        # Create a layout to combine summary and table
        layout = Layout()
        layout.split_column(
            Layout(summary, name="summary", size=3),
            Layout(table, name="table", ratio=1)
        )
        
        content = self.query_one(f"#{self.id}-content", Static)
        content.update(layout)


class MemoryPanel(DashboardPanel):
    """Panel for memory monitoring"""
    
    def __init__(self):
        """Initialize memory panel"""
        self.memory_monitor = MemoryMonitor(refresh_interval=1.0)
        super().__init__("MEMORY USAGE", self.memory_monitor, "memory-panel")
    
    async def update_content(self):
        """Update memory statistics"""
        table = self.memory_monitor.get_table()
        summary = self.memory_monitor.get_summary()
        
        # Create a layout to combine summary and table
        layout = Layout()
        layout.split_column(
            Layout(summary, name="summary", size=2),
            Layout(table, name="table", ratio=1)
        )
        
        content = self.query_one(f"#{self.id}-content", Static)
        content.update(layout)


class DiskPanel(DashboardPanel):
    """Panel for disk usage monitoring"""
    
    def __init__(self):
        """Initialize disk panel"""
        self.disk_usage = DiskUsage(refresh_interval=1.0)
        super().__init__("DISK USAGE & I/O", self.disk_usage, "disk-panel")
    
    async def update_content(self):
        """Update disk usage statistics"""
        table = self.disk_usage.get_table()
        summary = self.disk_usage.get_summary()
        
        # Create a layout to combine summary and table
        layout = Layout()
        layout.split_column(
            Layout(summary, name="summary", size=2),
            Layout(table, name="table", ratio=1)
        )
        
        content = self.query_one(f"#{self.id}-content", Static)
        content.update(layout)


class SocketPanel(DashboardPanel):
    """Panel for socket tracking"""
    
    def __init__(self):
        """Initialize socket panel"""
        self.socket_tracker = SocketTracker(refresh_interval=2.0)
        super().__init__("NETWORK CONNECTIONS", self.socket_tracker, "socket-panel")
    
    async def update_content(self):
        """Update socket information"""
        table = self.socket_tracker.get_table()
        summary = self.socket_tracker.get_summary()
        
        # Create a layout to combine summary and table
        layout = Layout()
        layout.split_column(
            Layout(summary, name="summary", size=1),
            Layout(table, name="table", ratio=1)
        )
        
        content = self.query_one(f"#{self.id}-content", Static)
        content.update(layout)


class PortsPanel(DashboardPanel):
    """Panel for ports and services monitoring"""
    
    def __init__(self):
        """Initialize ports panel"""
        self.ports_monitor = PortsMonitor(refresh_interval=2.0)
        super().__init__("LISTENING PORTS", self.ports_monitor, "ports-panel")
    
    async def update_content(self):
        """Update ports information"""
        table = self.ports_monitor.get_table()
        summary = self.ports_monitor.get_summary()
        
        # Create a layout to combine summary and table
        layout = Layout()
        layout.split_column(
            Layout(summary, name="summary", size=1),
            Layout(table, name="table", ratio=1)
        )
        
        content = self.query_one(f"#{self.id}-content", Static)
        content.update(layout)


class SystemHealthPanel(DashboardPanel):
    """Panel for system health monitoring"""
    
    def __init__(self):
        """Initialize system health panel"""
        self.system_health = SystemHealth(refresh_interval=2.0)
        super().__init__("SYSTEM HEALTH", self.system_health, "system-health-panel")
    
    async def update_content(self):
        """Update system health information"""
        table = self.system_health.get_table()
        summary = self.system_health.get_summary()
        
        # Create a layout to combine summary and table
        layout = Layout()
        layout.split_column(
            Layout(summary, name="summary", size=1),
            Layout(table, name="table", ratio=1)
        )
        
        content = self.query_one(f"#{self.id}-content", Static)
        content.update(layout)


class ContainerPanel(DashboardPanel):
    """Panel for container monitoring"""
    
    def __init__(self):
        """Initialize container panel"""
        self.container_monitor = ContainerMonitor(refresh_interval=2.0)
        super().__init__("CONTAINERS", self.container_monitor, "container-panel")
    
    async def update_content(self):
        """Update container information"""
        table = self.container_monitor.get_table()
        summary = self.container_monitor.get_summary()
        
        # Create a layout to combine summary and table
        layout = Layout()
        layout.split_column(
            Layout(summary, name="summary", size=1),
            Layout(table, name="table", ratio=1)
        )
        
        content = self.query_one(f"#{self.id}-content", Static)
        content.update(layout)


class VMPanel(DashboardPanel):
    """Panel for VM monitoring"""
    
    def __init__(self):
        """Initialize VM panel"""
        self.vm_monitor = VMMonitor(refresh_interval=2.0)
        super().__init__("VIRTUAL MACHINES", self.vm_monitor, "vm-panel")
    
    async def update_content(self):
        """Update VM information"""
        table = self.vm_monitor.get_table()
        summary = self.vm_monitor.get_summary()
        
        # Create a layout to combine summary and table
        layout = Layout()
        layout.split_column(
            Layout(summary, name="summary", size=1),
            Layout(table, name="table", ratio=1)
        )
        
        content = self.query_one(f"#{self.id}-content", Static)
        content.update(layout)


class SecurityPanel(DashboardPanel):
    """Panel for security monitoring"""
    
    def __init__(self):
        """Initialize security panel"""
        self.security_monitor = SecurityMonitor(refresh_interval=1.0)
        super().__init__("SECURITY ALERTS", self.security_monitor, "security-panel")
    
    async def update_content(self):
        """Update security information"""
        table = self.security_monitor.get_alerts_table()
        summary = self.security_monitor.get_summary()
        
        # Create a layout to combine summary and table
        layout = Layout()
        layout.split_column(
            Layout(summary, name="summary", size=1),
            Layout(table, name="table", ratio=1)
        )
        
        content = self.query_one(f"#{self.id}-content", Static)
        content.update(layout)


class ServiceManagerPanel(DashboardPanel):
    """Panel for service management"""
    
    def __init__(self):
        """Initialize service manager panel"""
        self.service_manager = ServiceManager(refresh_interval=2.0)
        super().__init__("SERVICES", self.service_manager, "service-manager-panel")
    
    async def update_content(self):
        """Update service information"""
        table = self.service_manager.get_table()
        summary = self.service_manager.get_summary()
        
        # Create a layout to combine summary and table
        layout = Layout()
        layout.split_column(
            Layout(summary, name="summary", size=1),
            Layout(table, name="table", ratio=1)
        )
        
        content = self.query_one(f"#{self.id}-content", Static)
        content.update(layout)


class DiskPanel(DashboardPanel):
    """Panel for disk usage monitoring"""
    
    def __init__(self):
        """Initialize disk usage panel"""
        self.disk_usage = DiskUsage(refresh_interval=1.0)
        super().__init__("DISK USAGE & I/O", self.disk_usage, "disk-panel")
    
    async def update_content(self):
        """Update disk statistics"""
        table = self.disk_usage.get_table()
        summary = self.disk_usage.get_summary()
        
        # Create a layout to combine summary and table
        layout = Layout()
        layout.split_column(
            Layout(summary, name="summary", size=2),
            Layout(table, name="table", ratio=1)
        )
        
        content = self.query_one(f"#{self.id}-content", Static)
        content.update(layout)


class NetDashApp(App):
    """NetDash Textual App"""
    
    CSS = """
    Screen {
        background: #121212;
    }

    #dashboard {
        layout: grid;
        grid-size: 6;
        grid-rows: 1fr 1fr 1fr 1fr 1fr 1fr;
        grid-columns: 1fr 1fr 1fr 1fr 1fr 1fr;
        height: 100%;
        padding: 0 1 0 1;
    }

    /* Resource Monitoring - Top Row */
    #cpu-panel {
        row-span: 1;
        column-span: 2;
        height: 100%;
        border: heavy $primary-darken-2;
        background: $surface-darken-1;
        overflow: auto;
    }

    #memory-panel {
        row-span: 1;
        column-span: 2;
        height: 100%;
        border: heavy $primary-darken-2;
        background: $surface-darken-1;
        overflow: auto;
    }
    
    #system-health-panel {
        row-span: 1;
        column-span: 2;
        height: 100%;
        border: heavy $primary-darken-2;
        background: $surface-darken-1;
        overflow: auto;
    }
    
    /* Network Row */
    #network-panel {
        row-span: 1;
        column-span: 2;
        height: 100%;
        border: heavy $primary-darken-2;
        background: $surface-darken-1;
        overflow: auto;
    }
    
    #socket-panel {
        row-span: 1;
        column-span: 2;
        height: 100%;
        border: heavy $primary-darken-2;
        background: $surface-darken-1;
        overflow: auto;
    }
    
    #ports-panel {
        row-span: 1;
        column-span: 2;
        height: 100%;
        border: heavy $primary-darken-2;
        background: $surface-darken-1;
        overflow: auto;
    }

    /* Storage Row */
    #disk-panel {
        row-span: 1;
        column-span: 3;
        height: 100%;
        border: heavy $primary-darken-2;
        background: $surface-darken-1;
        overflow: auto;
    }
    
    #container-panel {
        row-span: 1;
        column-span: 3;
        height: 100%;
        border: heavy $primary-darken-2;
        background: $surface-darken-1;
        overflow: auto;
    }
    
    /* Virtual Row */
    #vm-panel {
        row-span: 1;
        column-span: 3;
        height: 100%;
        border: heavy $primary-darken-2;
        background: $surface-darken-1;
        overflow: auto;
    }
    
    #service-manager-panel {
        row-span: 1;
        column-span: 3;
        height: 100%;
        border: heavy $primary-darken-2;
        background: $surface-darken-1;
        overflow: auto;
    }

    /* Security and Users Row */
    #login-panel {
        row-span: 1;
        column-span: 3;
        height: 100%;
        border: heavy $primary-darken-2;
        background: $surface-darken-1;
        overflow: auto;
    }
    
    #security-panel {
        row-span: 1;
        column-span: 3;
        height: 100%;
        border: heavy $primary-darken-2;
        background: $surface-darken-1;
        overflow: auto;
    }
    
    /* Log (Full Width) */
    #log-panel {
        row-span: 1;
        column-span: 6;
        height: 100%;
        border: heavy $primary-darken-2;
        background: $surface-darken-1;
        overflow: auto;
    }

    Header {
        background: $primary-darken-1;
        color: $text;
        padding: 0 1;
    }

    Footer {
        background: $primary-darken-1;
        color: $text;
        padding: 0 1;
    }
    
    .panel-title {
        dock: top;
        padding: 0 1;
        height: 1;
        background: $primary;
        color: $text;
        text-align: center;
        text-style: bold;
    }

    .panel-content {
        background: $surface;
        height: 1fr;
        overflow-y: auto;
        padding: 0 1 0 0;
    }
    """
    
    TITLE = "NETDASH"
    SUB_TITLE = "System Monitoring Dashboard"
    
    def __init__(self, *args, **kwargs):
        """Initialize the app"""
        super().__init__(*args, **kwargs)
        self.update_interval = 1.0  # seconds
    
    def compose(self) -> ComposeResult:
        """Compose the app layout"""
        yield Header(show_clock=True)
        
        with Container(id="dashboard"):
            # CPU monitor panel
            self.cpu_panel = CPUPanel()
            yield self.cpu_panel
            
            # Memory monitor panel
            self.memory_panel = MemoryPanel()
            yield self.memory_panel
            
            # Disk usage panel
            self.disk_panel = DiskPanel()
            yield self.disk_panel
            
            # System health panel
            self.system_health_panel = SystemHealthPanel()
            yield self.system_health_panel
            
            # Network stats panel
            self.network_panel = NetworkPanel()
            yield self.network_panel
            
            # Socket tracker panel
            self.socket_panel = SocketPanel()
            yield self.socket_panel
            
            # Ports monitor panel
            self.ports_panel = PortsPanel()
            yield self.ports_panel
            
            # Login panel
            self.login_panel = LoginPanel()
            yield self.login_panel
            
            # Log monitor panel
            self.log_panel = LogPanel()
            yield self.log_panel
            
            # Security panel
            self.security_panel = SecurityPanel()
            yield self.security_panel
            
            # Container monitor panel
            self.container_panel = ContainerPanel()
            yield self.container_panel
            
            # VM monitor panel
            self.vm_panel = VMPanel()
            yield self.vm_panel
            
            # Service manager panel
            self.service_manager_panel = ServiceManagerPanel()
            yield self.service_manager_panel
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Set up regular updates for panels after app is mounted"""
        self.set_interval(self.update_interval, self.update_panels)
    
    async def update_panels(self) -> None:
        """Update all dashboard panels"""
        await self.cpu_panel.update_content()
        await self.memory_panel.update_content()
        await self.disk_panel.update_content()
        await self.system_health_panel.update_content()
        await self.network_panel.update_content()
        await self.socket_panel.update_content()
        await self.ports_panel.update_content()
        await self.login_panel.update_content()
        await self.log_panel.update_content()
        await self.security_panel.update_content()
        await self.container_panel.update_content()
        await self.vm_panel.update_content()
        await self.service_manager_panel.update_content()
        

class RichDashboard:
    """Rich-based dashboard as an alternative to Textual"""
    
    def __init__(self, update_interval: float = 1.0, custom_log_file: str = None):
        """
        Initialize the dashboard
        
        Args:
            update_interval: Update interval in seconds
            custom_log_file: Optional path to a custom log file
        """
        self.console = Console(highlight=False)
        self.update_interval = update_interval
        self.layout = self._create_layout()
        
        # Initialize components
        self.cpu_monitor = CPUMonitor(refresh_interval=update_interval)
        self.memory_monitor = MemoryMonitor(refresh_interval=update_interval)
        self.disk_usage = DiskUsage(refresh_interval=update_interval)
        self.system_health = SystemHealth(refresh_interval=update_interval)
        self.network_stats = NetworkStats(refresh_interval=update_interval)
        self.socket_tracker = SocketTracker(refresh_interval=update_interval)
        self.ports_monitor = PortsMonitor(refresh_interval=update_interval)
        self.login_tracker = LoginTracker()
        self.container_monitor = ContainerMonitor(refresh_interval=update_interval)
        self.vm_monitor = VMMonitor(refresh_interval=update_interval)
        self.security_monitor = SecurityMonitor(refresh_interval=update_interval)
        self.service_manager = ServiceManager(refresh_interval=update_interval)
        
        # Create a custom configuration for log monitor
        log_config = LogMonitorConfig(
            # Use custom log file if provided, otherwise default
            log_file=custom_log_file or "/var/log/auth.log",
            # Fallback to a sample log file if it exists
            fallback_log_file=os.path.join(HOME_DIR, "sample_auth.log"),
            # Refresh every second
            refresh_interval=update_interval
        )
        self.log_monitor = LogMonitor(log_config)
    
    def _create_layout(self) -> Layout:
        """
        Create the main layout
        
        Returns:
            Rich Layout object
        """
        layout = Layout(name="root")
        
        # Split into sections
        layout.split(
            Layout(name="resources", ratio=1),   # CPU, Memory, System Health
            Layout(name="networking", ratio=1),  # Network, Sockets, Ports
            Layout(name="storage", ratio=1),     # Disk, Containers
            Layout(name="virt", ratio=1),        # VMs, Services
            Layout(name="users", ratio=1),       # Logins, Security
            Layout(name="logs", ratio=1),        # Log monitor (larger)
        )
        
        # Resources row: CPU, Memory, System Health
        layout["resources"].split_row(
            Layout(name="cpu", ratio=1),
            Layout(name="memory", ratio=1),
            Layout(name="system_health", ratio=1),
        )
        
        # Networking row: Network Stats, Socket Tracker, Ports Monitor
        layout["networking"].split_row(
            Layout(name="network", ratio=1),
            Layout(name="sockets", ratio=1),
            Layout(name="ports", ratio=1),
        )
        
        # Storage row: Disk Usage, Container Monitor
        layout["storage"].split_row(
            Layout(name="disk", ratio=1),
            Layout(name="containers", ratio=1),
        )
        
        # Virtualization row: VMs, Services
        layout["virt"].split_row(
            Layout(name="vms", ratio=1),
            Layout(name="services", ratio=1),
        )
        
        # Users row: Logins, Security
        layout["users"].split_row(
            Layout(name="logins", ratio=1),
            Layout(name="security", ratio=1),
        )
        
        # Logs row (full width)
        layout["logs"].update(Layout(name="log_monitor", ratio=1))
        
        return layout
    
    def _update_layout(self) -> None:
        """Update all panels in the layout"""
        # Update CPU monitor
        cpu_table = self.cpu_monitor.get_table()
        cpu_summary = self.cpu_monitor.get_summary()
        
        cpu_layout = Layout()
        cpu_layout.split_column(
            Layout(cpu_summary, name="summary", size=3),
            Layout(cpu_table, name="table", ratio=1)
        )
        
        self.layout["resources"]["cpu"].update(
            Panel(
                cpu_layout,
                title="[bold white]CPU USAGE & LOAD[/bold white]", 
                border_style="bright_green", 
                box=box.HEAVY,
                padding=(0, 1)
            )
        )
        
        # Update memory monitor
        memory_table = self.memory_monitor.get_table()
        memory_summary = self.memory_monitor.get_summary()
        
        memory_layout = Layout()
        memory_layout.split_column(
            Layout(memory_summary, name="summary", size=2),
            Layout(memory_table, name="table", ratio=1)
        )
        
        self.layout["resources"]["memory"].update(
            Panel(
                memory_layout,
                title="[bold white]MEMORY USAGE[/bold white]", 
                border_style="bright_magenta", 
                box=box.HEAVY,
                padding=(0, 1)
            )
        )
        
        # Update system health
        system_table = self.system_health.get_table()
        system_summary = self.system_health.get_summary()
        
        system_layout = Layout()
        system_layout.split_column(
            Layout(system_summary, name="summary", size=1),
            Layout(system_table, name="table", ratio=1)
        )
        
        self.layout["resources"]["system_health"].update(
            Panel(
                system_layout,
                title="[bold white]SYSTEM HEALTH[/bold white]", 
                border_style="bright_red", 
                box=box.HEAVY,
                padding=(0, 1)
            )
        )
        
        # Update network stats
        net_table = self.network_stats.get_table()
        net_summary = self.network_stats.get_summary()
        
        net_layout = Layout()
        net_layout.split_column(
            Layout(net_summary, name="summary", size=1),
            Layout(net_table, name="table", ratio=1)
        )
        
        self.layout["networking"]["network"].update(
            Panel(
                net_layout,
                title="[bold white]NETWORK STATISTICS[/bold white]", 
                border_style="bright_blue", 
                box=box.HEAVY,
                padding=(0, 1)
            )
        )
        
        # Update socket tracker
        socket_table = self.socket_tracker.get_table()
        socket_summary = self.socket_tracker.get_summary()
        
        socket_layout = Layout()
        socket_layout.split_column(
            Layout(socket_summary, name="summary", size=1),
            Layout(socket_table, name="table", ratio=1)
        )
        
        self.layout["networking"]["sockets"].update(
            Panel(
                socket_layout,
                title="[bold white]NETWORK CONNECTIONS[/bold white]", 
                border_style="bright_cyan", 
                box=box.HEAVY,
                padding=(0, 1)
            )
        )
        
        # Update ports monitor
        ports_table = self.ports_monitor.get_table()
        ports_summary = self.ports_monitor.get_summary()
        
        ports_layout = Layout()
        ports_layout.split_column(
            Layout(ports_summary, name="summary", size=1),
            Layout(ports_table, name="table", ratio=1)
        )
        
        self.layout["networking"]["ports"].update(
            Panel(
                ports_layout,
                title="[bold white]LISTENING PORTS[/bold white]", 
                border_style="bright_blue", 
                box=box.HEAVY,
                padding=(0, 1)
            )
        )
        
        # Update disk usage
        disk_table = self.disk_usage.get_table()
        disk_summary = self.disk_usage.get_summary()
        
        disk_layout = Layout()
        disk_layout.split_column(
            Layout(disk_summary, name="summary", size=2),
            Layout(disk_table, name="table", ratio=1)
        )
        
        self.layout["storage"]["disk"].update(
            Panel(
                disk_layout,
                title="[bold white]DISK USAGE & I/O[/bold white]", 
                border_style="bright_yellow", 
                box=box.HEAVY,
                padding=(0, 1)
            )
        )
        
        # Update container monitor
        container_table = self.container_monitor.get_table()
        container_summary = self.container_monitor.get_summary()
        
        container_layout = Layout()
        container_layout.split_column(
            Layout(container_summary, name="summary", size=1),
            Layout(container_table, name="table", ratio=1)
        )
        
        self.layout["storage"]["containers"].update(
            Panel(
                container_layout,
                title="[bold white]CONTAINERS[/bold white]", 
                border_style="bright_magenta", 
                box=box.HEAVY,
                padding=(0, 1)
            )
        )
        
        # Update VM monitor
        vm_table = self.vm_monitor.get_table()
        vm_summary = self.vm_monitor.get_summary()
        
        vm_layout = Layout()
        vm_layout.split_column(
            Layout(vm_summary, name="summary", size=1),
            Layout(vm_table, name="table", ratio=1)
        )
        
        self.layout["virt"]["vms"].update(
            Panel(
                vm_layout,
                title="[bold white]VIRTUAL MACHINES[/bold white]", 
                border_style="bright_green", 
                box=box.HEAVY,
                padding=(0, 1)
            )
        )
        
        # Update services manager
        service_table = self.service_manager.get_table()
        service_summary = self.service_manager.get_summary()
        
        service_layout = Layout()
        service_layout.split_column(
            Layout(service_summary, name="summary", size=1),
            Layout(service_table, name="table", ratio=1)
        )
        
        self.layout["virt"]["services"].update(
            Panel(
                service_layout,
                title="[bold white]SERVICES[/bold white]", 
                border_style="bright_cyan", 
                box=box.HEAVY,
                padding=(0, 1)
            )
        )
        
        # Update login information
        active_table = self.login_tracker.get_active_logins_table()
        history_table = self.login_tracker.get_login_history_table()
        
        login_layout = Layout()
        login_layout.split_column(
            Layout(active_table, name="active", ratio=1),
            Layout(history_table, name="history", ratio=1)
        )
        
        self.layout["users"]["logins"].update(
            Panel(
                login_layout,
                title="[bold white]USER LOGIN INFORMATION[/bold white]",
                border_style="bright_blue",
                box=box.HEAVY,
                padding=(0, 1)
            )
        )
        
        # Update security monitor
        security_table = self.security_monitor.get_alerts_table()
        security_summary = self.security_monitor.get_summary()
        
        security_layout = Layout()
        security_layout.split_column(
            Layout(security_summary, name="summary", size=1),
            Layout(security_table, name="table", ratio=1)
        )
        
        self.layout["users"]["security"].update(
            Panel(
                security_layout,
                title="[bold white]SECURITY ALERTS[/bold white]",
                border_style="bright_red",
                box=box.HEAVY,
                padding=(0, 1)
            )
        )
        
        # Update log monitor
        self.log_monitor.update()
        log_panel = self.log_monitor.get_panel()
        
        # Extract the content from the panel and put it in our own panel
        self.layout["logs"]["log_monitor"].update(
            Panel(
                log_panel.renderable,
                title="[bold white]SECURITY LOG MONITOR[/bold white]",
                border_style="bright_yellow",
                box=box.HEAVY,
                padding=(0, 1)
            )
        )
    
    async def run(self) -> None:
        """Run the dashboard"""
        with Live(self.layout, refresh_per_second=1/self.update_interval, screen=True) as live:
            try:
                while True:
                    self._update_layout()
                    await asyncio.sleep(self.update_interval)
            except KeyboardInterrupt:
                pass


def main(use_textual: bool = True, custom_log_file: str = None) -> None:
    """
    Main function to run the dashboard
    
    Args:
        use_textual: Whether to use the Textual-based or Rich-based dashboard
        custom_log_file: Optional path to a custom log file
    """
    # Parse any command-line arguments
    debug_mode = "--debug" in sys.argv
    no_color = "--no-color" in sys.argv
    
    if debug_mode:
        print("Debug mode enabled")
        
    if no_color:
        os.environ["NO_COLOR"] = "1"
        
    # Store custom log file in environment variable for panels to access
    if custom_log_file:
        os.environ["NETDASH_LOG_FILE"] = custom_log_file
    
    try:
        if use_textual:
            # Run the Textual app
            app = NetDashApp()
            app.run()
        else:
            # Run the Rich-based dashboard
            dashboard = RichDashboard(update_interval=1.0, custom_log_file=custom_log_file)
            
            # Get event loop
            loop = asyncio.get_event_loop()
            loop.run_until_complete(dashboard.run())
    except KeyboardInterrupt:
        print("\nExiting NetDash...")
    except Exception as e:
        print(f"Error: {str(e)}")
        if debug_mode:
            import traceback
            traceback.print_exc()
            

if __name__ == "__main__":
    # Default to Textual UI, but fall back to Rich if specified
    use_textual = "--rich-only" not in sys.argv
    
    # Check for custom log file
    custom_log_file = None
    for i, arg in enumerate(sys.argv):
        if arg == "--log-file" and i + 1 < len(sys.argv):
            custom_log_file = sys.argv[i + 1]
            break
    
    main(use_textual, custom_log_file)
