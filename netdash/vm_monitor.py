#!/usr/bin/env python3
"""
VM Monitor Module

Monitors virtual machines across different hypervisors:
- KVM/Libvirt, VirtualBox, QEMU detection
- VM inventory with state and resource allocation
- Real-time stats for CPU, memory, and disk usage
- VM state controls and snapshot management
"""

import os
import sys
import time
import asyncio
import subprocess
import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional, Any, Set
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import BarColumn, Progress, TextColumn
from rich import box

# VM status colors
STATUS_COLORS = {
    'running': 'green',
    'idle': 'green',
    'paused': 'yellow',
    'shutdown': 'cyan',
    'shutoff': 'cyan',
    'crashed': 'red',
    'dying': 'red',
    'pmsuspended': 'blue',
    'saved': 'blue',
    'powered off': 'cyan',
    'aborted': 'red',
}

# Hypervisor type icons
HYPERVISOR_ICONS = {
    'libvirt': '🔷',
    'qemu': '🔶',
    'kvm': '🔷',
    'virtualbox': '📦',
    'vmware': '🔹',
    'xen': '🔸',
    'unknown': '❓',
}


class VMMonitor:
    """Monitor and display virtual machine information"""
    
    def __init__(self, refresh_interval: float = 2.0):
        """
        Initialize the VM monitor
        
        Args:
            refresh_interval: How often to refresh the data (in seconds)
        """
        self.refresh_interval = refresh_interval
        self.console = Console()
        self._last_update = 0
        self._vms = []
        
        # Check for available hypervisors
        self._has_libvirt = self._check_command('virsh')
        self._has_vbox = self._check_command('VBoxManage')
        
        # Cache for VM details
        self._vm_details = {}
        self._vm_stats = {}
        
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
        """Update VM information"""
        # Only update if the refresh interval has passed
        current_time = time.time()
        if current_time - self._last_update >= self.refresh_interval:
            self._last_update = current_time
            
            # Reset VM list
            self._vms = []
            
            # Check libvirt VMs
            if self._has_libvirt:
                self._update_libvirt_vms()
                
            # Check VirtualBox VMs
            if self._has_vbox:
                self._update_virtualbox_vms()
    
    def _update_libvirt_vms(self) -> None:
        """Update information about libvirt VMs"""
        try:
            # Get list of all VMs
            cmd = ['virsh', 'list', '--all', '--name']
            output = subprocess.check_output(cmd, text=True)
            
            # Process each VM
            for vm_name in output.strip().split('\n'):
                if not vm_name:
                    continue
                    
                # Get VM info
                vm_info = self._get_libvirt_vm_info(vm_name)
                if vm_info:
                    self._vms.append(vm_info)
                    
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    
    def _get_libvirt_vm_info(self, vm_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a libvirt VM
        
        Args:
            vm_name: Name of the VM
            
        Returns:
            Dictionary with VM information or None
        """
        try:
            # Get VM state
            state_cmd = ['virsh', 'domstate', vm_name]
            state_output = subprocess.check_output(state_cmd, text=True).strip()
            
            # Get VM XML definition
            xml_cmd = ['virsh', 'dumpxml', vm_name]
            xml_output = subprocess.check_output(xml_cmd, text=True)
            
            # Parse XML to get VM details
            root = ET.fromstring(xml_output)
            
            # Get vCPU count
            vcpu_elem = root.find('./vcpu')
            vcpu_count = int(vcpu_elem.text) if vcpu_elem is not None else "N/A"
            
            # Get memory allocation in MB
            memory_elem = root.find('./memory')
            memory = "N/A"
            if memory_elem is not None:
                memory_value = int(memory_elem.text)
                memory_unit = memory_elem.attrib.get('unit', 'KiB')
                
                # Convert to MB
                if memory_unit == 'KiB':
                    memory = f"{memory_value / 1024:.0f} MB"
                elif memory_unit == 'MiB':
                    memory = f"{memory_value:.0f} MB"
                elif memory_unit == 'GiB':
                    memory = f"{memory_value * 1024:.0f} MB"
                    
            # Get disk info
            disks = []
            disk_elems = root.findall('.//disk')
            for disk in disk_elems:
                disk_type = disk.attrib.get('type')
                if disk_type == 'file':
                    source = disk.find('./source')
                    if source is not None and 'file' in source.attrib:
                        disks.append(source.attrib['file'])
                        
            # Get network info
            networks = []
            net_elems = root.findall('.//interface')
            for iface in net_elems:
                net_type = iface.attrib.get('type')
                if net_type == 'network':
                    source = iface.find('./source')
                    if source is not None and 'network' in source.attrib:
                        networks.append(source.attrib['network'])
            
            # Get stats if VM is running
            stats = None
            if state_output == 'running':
                stats = self._get_libvirt_vm_stats(vm_name)
                
            # Get snapshot count
            snapshot_cmd = ['virsh', 'snapshot-list', vm_name, '--name']
            try:
                snapshot_output = subprocess.check_output(snapshot_cmd, text=True)
                snapshot_count = len([s for s in snapshot_output.strip().split('\n') if s])
            except subprocess.SubprocessError:
                snapshot_count = 0
                
            return {
                'name': vm_name,
                'type': 'libvirt',
                'hypervisor': 'KVM/QEMU',
                'status': state_output,
                'vcpus': vcpu_count,
                'memory': memory,
                'disks': len(disks),
                'networks': networks,
                'snapshots': snapshot_count,
                'stats': stats
            }
            
        except (subprocess.SubprocessError, ET.ParseError):
            return None
    
    def _get_libvirt_vm_stats(self, vm_name: str) -> Optional[Dict[str, Any]]:
        """
        Get runtime stats for a libvirt VM
        
        Args:
            vm_name: Name of the VM
            
        Returns:
            Dictionary with VM stats or None
        """
        try:
            # Get CPU stats
            cpu_cmd = ['virsh', 'domstats', vm_name, '--cpu-total']
            cpu_output = subprocess.check_output(cpu_cmd, text=True)
            
            # Get memory stats
            mem_cmd = ['virsh', 'domstats', vm_name, '--balloon']
            mem_output = subprocess.check_output(mem_cmd, text=True)
            
            # Get block stats (disk)
            block_cmd = ['virsh', 'domstats', vm_name, '--block']
            block_output = subprocess.check_output(block_cmd, text=True)
            
            # Get net stats
            net_cmd = ['virsh', 'domstats', vm_name, '--net']
            net_output = subprocess.check_output(net_cmd, text=True)
            
            # Parse CPU usage
            cpu_percent = "N/A"
            cpu_time = 0
            for line in cpu_output.strip().split('\n'):
                if 'cpu.time=' in line:
                    # Extract CPU time in nanoseconds
                    cpu_time = int(line.split('=')[1])
                    
                    # Calculate percentage based on time delta from last update
                    if vm_name in self._vm_stats and 'cpu_time' in self._vm_stats[vm_name]:
                        prev_time = self._vm_stats[vm_name]['cpu_time']
                        time_delta = cpu_time - prev_time
                        
                        # CPU usage is delta / interval in ns * 100 / num of vCPUs
                        usage = time_delta / (self.refresh_interval * 1_000_000_000)
                        cpu_percent = f"{usage * 100:.1f}%"
            
            # Parse memory usage
            mem_used = 0
            mem_total = 1  # Avoid division by zero
            for line in mem_output.strip().split('\n'):
                if 'balloon.current=' in line:
                    mem_used = int(line.split('=')[1])
                if 'balloon.maximum=' in line:
                    mem_total = int(line.split('=')[1])
                    
            # Memory in MB and percentage
            mem_used_mb = mem_used / 1024
            mem_total_mb = mem_total / 1024
            mem_percent = (mem_used / mem_total) * 100 if mem_total > 0 else 0
            
            # Parse disk I/O
            read_bytes = 0
            write_bytes = 0
            for line in block_output.strip().split('\n'):
                if 'block.0.rd.bytes=' in line:
                    read_bytes = int(line.split('=')[1])
                if 'block.0.wr.bytes=' in line:
                    write_bytes = int(line.split('=')[1])
                    
            # Calculate disk I/O rates
            disk_read_rate = "N/A"
            disk_write_rate = "N/A"
            
            if vm_name in self._vm_stats:
                prev_stats = self._vm_stats[vm_name]
                if 'read_bytes' in prev_stats and 'write_bytes' in prev_stats:
                    read_delta = read_bytes - prev_stats['read_bytes']
                    write_delta = write_bytes - prev_stats['write_bytes']
                    
                    read_rate = read_delta / self.refresh_interval / (1024 * 1024)  # MB/s
                    write_rate = write_delta / self.refresh_interval / (1024 * 1024)  # MB/s
                    
                    disk_read_rate = f"{read_rate:.2f} MB/s"
                    disk_write_rate = f"{write_rate:.2f} MB/s"
            
            # Parse network I/O
            rx_bytes = 0
            tx_bytes = 0
            for line in net_output.strip().split('\n'):
                if 'net.0.rx.bytes=' in line:
                    rx_bytes = int(line.split('=')[1])
                if 'net.0.tx.bytes=' in line:
                    tx_bytes = int(line.split('=')[1])
            
            # Calculate network I/O rates
            net_rx_rate = "N/A"
            net_tx_rate = "N/A"
            
            if vm_name in self._vm_stats:
                prev_stats = self._vm_stats[vm_name]
                if 'rx_bytes' in prev_stats and 'tx_bytes' in prev_stats:
                    rx_delta = rx_bytes - prev_stats['rx_bytes']
                    tx_delta = tx_bytes - prev_stats['tx_bytes']
                    
                    rx_rate = rx_delta / self.refresh_interval / (1024 * 1024)  # MB/s
                    tx_rate = tx_delta / self.refresh_interval / (1024 * 1024)  # MB/s
                    
                    net_rx_rate = f"{rx_rate:.2f} MB/s"
                    net_tx_rate = f"{tx_rate:.2f} MB/s"
            
            # Store current stats for next update
            self._vm_stats[vm_name] = {
                'cpu_time': cpu_time,
                'read_bytes': read_bytes,
                'write_bytes': write_bytes,
                'rx_bytes': rx_bytes,
                'tx_bytes': tx_bytes
            }
            
            return {
                'cpu': cpu_percent,
                'memory_used': f"{mem_used_mb:.0f} MB",
                'memory_total': f"{mem_total_mb:.0f} MB",
                'memory_percent': f"{mem_percent:.1f}%",
                'disk_read': disk_read_rate,
                'disk_write': disk_write_rate,
                'net_rx': net_rx_rate,
                'net_tx': net_tx_rate
            }
            
        except (subprocess.SubprocessError, ValueError):
            return None
    
    def _update_virtualbox_vms(self) -> None:
        """Update information about VirtualBox VMs"""
        try:
            # Get list of all VMs
            cmd = ['VBoxManage', 'list', 'vms']
            output = subprocess.check_output(cmd, text=True)
            
            # Extract VM names and UUIDs
            for line in output.strip().split('\n'):
                if not line:
                    continue
                    
                # Format: "VM Name" {UUID}
                parts = line.split(' {')
                if len(parts) == 2:
                    vm_name = parts[0].strip('"')
                    vm_uuid = '{' + parts[1].rstrip()
                    
                    # Get VM info
                    vm_info = self._get_virtualbox_vm_info(vm_name, vm_uuid)
                    if vm_info:
                        self._vms.append(vm_info)
                    
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    
    def _get_virtualbox_vm_info(self, vm_name: str, vm_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a VirtualBox VM
        
        Args:
            vm_name: Name of the VM
            vm_uuid: UUID of the VM
            
        Returns:
            Dictionary with VM information or None
        """
        try:
            # Get VM info
            info_cmd = ['VBoxManage', 'showvminfo', vm_name, '--machinereadable']
            info_output = subprocess.check_output(info_cmd, text=True)
            
            # Parse machine-readable output
            info = {}
            for line in info_output.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    info[key] = value.strip('"')
                    
            # Extract key information
            status = info.get('VMState', 'unknown').lower()
            vcpus = info.get('cpus', 'N/A')
            memory = f"{int(info.get('memory', 0))} MB"
            
            # Count disks
            disk_count = 0
            for key in info:
                if key.startswith('SATA') and key.endswith('-ImageUUID'):
                    disk_count += 1
                    
            # Get network adapters
            networks = []
            for i in range(8):  # Check up to 8 network adapters
                adapter_key = f'nic{i+1}'
                if adapter_key in info and info[adapter_key] != 'none':
                    networks.append(info[adapter_key])
            
            # Get running stats
            stats = None
            if status == 'running':
                stats = self._get_virtualbox_vm_stats(vm_name)
                
            # Get snapshot count
            snapshot_cmd = ['VBoxManage', 'snapshot', vm_name, 'list']
            try:
                snapshot_output = subprocess.check_output(snapshot_cmd, text=True)
                snapshot_count = snapshot_output.count('Name:')
            except subprocess.SubprocessError:
                snapshot_count = 0
                
            return {
                'name': vm_name,
                'type': 'virtualbox',
                'hypervisor': 'VirtualBox',
                'status': status,
                'vcpus': vcpus,
                'memory': memory,
                'disks': disk_count,
                'networks': networks,
                'snapshots': snapshot_count,
                'stats': stats
            }
            
        except subprocess.SubprocessError:
            return None
    
    def _get_virtualbox_vm_stats(self, vm_name: str) -> Optional[Dict[str, Any]]:
        """
        Get runtime stats for a VirtualBox VM
        
        Args:
            vm_name: Name of the VM
            
        Returns:
            Dictionary with VM stats or None
        """
        try:
            # VirtualBox doesn't provide detailed real-time stats easily,
            # so we'll return placeholder values
            return {
                'cpu': 'N/A',
                'memory_used': 'N/A',
                'memory_total': 'N/A',
                'memory_percent': 'N/A',
                'disk_read': 'N/A',
                'disk_write': 'N/A',
                'net_rx': 'N/A',
                'net_tx': 'N/A'
            }
        except:
            return None
    
    def vm_action(self, vm_name: str, action: str) -> Tuple[bool, str]:
        """
        Perform an action on a VM
        
        Args:
            vm_name: Name of the VM
            action: start, stop, pause, resume, reset
            
        Returns:
            Tuple of (success, message)
        """
        # Find VM in our list
        vm = None
        for v in self._vms:
            if v['name'] == vm_name:
                vm = v
                break
                
        if not vm:
            return False, f"VM '{vm_name}' not found"
            
        # Handle action based on hypervisor type
        if vm['type'] == 'libvirt':
            return self._libvirt_vm_action(vm_name, action)
        elif vm['type'] == 'virtualbox':
            return self._virtualbox_vm_action(vm_name, action)
        else:
            return False, f"Unsupported hypervisor type: {vm['type']}"
    
    def _libvirt_vm_action(self, vm_name: str, action: str) -> Tuple[bool, str]:
        """
        Perform an action on a libvirt VM
        
        Args:
            vm_name: Name of the VM
            action: start, stop, pause, resume, reset
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Map actions to virsh commands
            command_map = {
                'start': 'start',
                'stop': 'shutdown',
                'force-stop': 'destroy',
                'pause': 'suspend',
                'resume': 'resume',
                'reset': 'reset',
            }
            
            if action not in command_map:
                return False, f"Invalid action: {action}"
                
            cmd = ['virsh', command_map[action], vm_name]
            subprocess.check_call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            return True, f"VM '{vm_name}' {action} successful"
            
        except subprocess.SubprocessError as e:
            return False, f"Failed to {action} VM: {str(e)}"
    
    def _virtualbox_vm_action(self, vm_name: str, action: str) -> Tuple[bool, str]:
        """
        Perform an action on a VirtualBox VM
        
        Args:
            vm_name: Name of the VM
            action: start, stop, pause, resume, reset
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Map actions to VBoxManage commands
            command_map = {
                'start': ['startvm', vm_name, '--type', 'headless'],
                'stop': ['controlvm', vm_name, 'acpipowerbutton'],
                'force-stop': ['controlvm', vm_name, 'poweroff'],
                'pause': ['controlvm', vm_name, 'pause'],
                'resume': ['controlvm', vm_name, 'resume'],
                'reset': ['controlvm', vm_name, 'reset'],
            }
            
            if action not in command_map:
                return False, f"Invalid action: {action}"
                
            cmd = ['VBoxManage'] + command_map[action]
            subprocess.check_call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            return True, f"VM '{vm_name}' {action} successful"
            
        except subprocess.SubprocessError as e:
            return False, f"Failed to {action} VM: {str(e)}"
    
    def get_table(self) -> Table:
        """
        Generate a rich table with VM information
        
        Returns:
            Rich Table object with VM data
        """
        self.update()
        
        # Create VM table
        table = Table(
            box=box.SIMPLE,
            title="",
            show_header=True,
            header_style="bold magenta",
            show_edge=False,
            padding=(0, 1),
        )
        
        # Define columns
        table.add_column("Type", width=8)
        table.add_column("VM Name", style="cyan", width=20)
        table.add_column("Status", width=10)
        table.add_column("vCPUs", width=5)
        table.add_column("Memory", width=10)
        table.add_column("CPU Usage", width=10)
        table.add_column("Mem Usage", width=10)
        table.add_column("Snapshots", width=9)
        
        # Check if we have data to display
        if not self._vms:
            if not self._has_libvirt and not self._has_vbox:
                table.add_row(
                    "N/A", 
                    "[yellow]No hypervisors detected[/yellow]", 
                    "N/A", 
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A"
                )
            else:
                table.add_row(
                    "N/A",
                    "No VMs found",
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A"
                )
            return table
            
        # Sort VMs by status (running first) and then name
        sorted_vms = sorted(
            self._vms, 
            key=lambda v: (0 if v['status'] == 'running' else 1, v['name'])
        )
        
        # Add rows for each VM
        for vm in sorted_vms:
            # Get hypervisor icon
            icon = HYPERVISOR_ICONS.get(vm['type'], '❓')
            
            # Get status with color
            status = vm['status']
            status_color = STATUS_COLORS.get(status, 'white')
            status_display = f"[{status_color}]{status}[/{status_color}]"
            
            # Get resource usage if available
            cpu_usage = "N/A"
            mem_usage = "N/A"
            
            if vm['stats']:
                cpu_usage = vm['stats'].get('cpu', 'N/A')
                mem_usage = vm['stats'].get('memory_percent', 'N/A')
                
            # Add row
            table.add_row(
                f"{icon} {vm['type']}",
                vm['name'],
                status_display,
                str(vm['vcpus']),
                str(vm['memory']),
                cpu_usage,
                mem_usage,
                str(vm['snapshots'])
            )
            
        return table
    
    def get_summary(self) -> Text:
        """
        Generate a summary of VM status
        
        Returns:
            Rich Text object with VM summary
        """
        self.update()
        
        # Count VMs by type and status
        total = len(self._vms)
        running = sum(1 for v in self._vms if v['status'] == 'running')
        libvirt_count = sum(1 for v in self._vms if v['type'] == 'libvirt')
        vbox_count = sum(1 for v in self._vms if v['type'] == 'virtualbox')
        
        summary = Text()
        summary.append("Virtual Machines: ")
        summary.append(f"{total} total ", "bold white")
        summary.append(f"({running} running) ", "green")
        
        if libvirt_count > 0:
            summary.append(f"KVM: {libvirt_count} ", "blue")
            
        if vbox_count > 0:
            summary.append(f"VBox: {vbox_count}", "cyan")
            
        return summary
    
    def get_panel(self) -> Panel:
        """
        Return a panel with VM information
        
        Returns:
            Rich Panel with table of VMs
        """
        table = self.get_table()
        summary = self.get_summary()
        
        panel_content = Text()
        panel_content.append(summary)
        panel_content.append("\n\n")
        panel_content.append(str(table))
        
        return Panel(
            panel_content,
            title="[bold]Virtual Machine Monitor[/bold]",
            border_style="magenta",
            box=box.ROUNDED
        )


async def _display_vm_info() -> None:
    """Display VM information in a live view"""
    console = Console()
    monitor = VMMonitor(refresh_interval=2.0)
    
    with Live(console=console, screen=True, refresh_per_second=0.5) as live:
        try:
            while True:
                panel = monitor.get_panel()
                live.update(panel)
                await asyncio.sleep(2.0)
        except KeyboardInterrupt:
            pass


def main() -> None:
    """Run the VM monitor as a standalone component"""
    try:
        if os.geteuid() != 0:
            print("[bold yellow]WARNING: Running without root privileges. VM control may be limited.[/bold yellow]")
        
        asyncio.run(_display_vm_info())
    except KeyboardInterrupt:
        print("\nExiting VM Monitor...")


if __name__ == "__main__":
    main()
