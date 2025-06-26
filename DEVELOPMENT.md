# NetDash Development Log

## Project Overview
NetDash is a modular Linux terminal tool similar to `htop`, but focused on real-time network activity, user login monitoring, and log-based alerts.

## Project Structure
```
netdash/
├── debian/                 # Debian packaging files
├── netdash/                # Main package directory
│   ├── __init__.py         # Package initialization
│   ├── __main__.py         # Entry point
│   ├── dashboard.py        # Main dashboard UI
│   ├── cpu_monitor.py      # CPU monitoring module
│   ├── memory_monitor.py   # Memory usage monitoring module
│   ├── disk_usage.py       # Disk usage and I/O module
│   ├── network_stats.py    # Network statistics module
│   ├── socket_tracker.py   # TCP/UDP socket tracking module
│   ├── ports_monitor.py    # Listening ports monitor module
│   ├── system_health.py    # System health monitoring module
│   ├── service_manager.py  # Systemd service management module
│   ├── log_monitor.py      # Log monitoring module
│   ├── login_tracker.py    # Login tracking module
│   ├── container_monitor.py # Container monitoring module
│   ├── vm_monitor.py       # VM monitoring module
│   └── security_monitor.py # Security monitoring module
├── tests/                  # Test directory
│   ├── __init__.py         # Test package initialization
│   ├── test_cpu_monitor.py # CPU monitor tests
│   ├── test_memory_monitor.py # Memory monitor tests
│   ├── test_disk_usage.py  # Disk usage tests
│   ├── test_log_monitor.py # Log monitor tests
│   ├── test_login_tracker.py # Login tracker tests
│   └── test_network_stats.py # Network stats tests
├── tools/                  # Utility scripts
│   └── generate_sample_log.py # Test log generator
├── .gitignore              # Git ignore file
├── pyproject.toml          # Project configuration
├── pytest.ini              # Pytest configuration
├── README.md               # Project documentation
├── DEVELOPMENT.md          # Development documentation
├── requirements.txt        # Dependency list
└── run.sh                  # Convenience script for running the app
```

## Modules

### Core System Monitoring

### 1. CPU Monitor (`cpu_monitor.py`)
- Monitors per-core CPU usage and overall load
- Shows system load averages (1, 5, 15 minute)
- Updates in real-time with configurable refresh rate
- Includes standalone mode for use in terminal

### 2. Memory Monitor (`memory_monitor.py`)
- Tracks RAM, swap, buffers, and cache usage
- Shows memory statistics in readable format
- Visualizes memory usage with progress bars
- Includes standalone mode for use in terminal

### 3. Disk Usage (`disk_usage.py`)
- Monitors filesystem usage across mounted partitions
- Tracks disk I/O statistics (read/write operations)
- Shows filesystem types and mount points
- Includes standalone mode for use in terminal

### 4. System Health (`system_health.py`)
- Monitors system uptime and load
- Tracks system temperatures from sensors
- Checks RAID and SMART disk health status
- Includes standalone mode for use in terminal

### Networking Modules

### 5. Network Stats (`network_stats.py`)
- Uses `psutil` to monitor network interfaces
- Shows bandwidth in/out per interface
- Updates in real-time with configurable refresh rate
- Includes standalone test function

### 6. Socket Tracker (`socket_tracker.py`)
- Monitors active TCP/UDP connections
- Maps sockets to running processes
- Shows connection status and remote addresses
- Includes process owner and command information

### 7. Ports Monitor (`ports_monitor.py`)
- Visualizes listening ports and services
- Maps ports to processes and services
- Shows port states (listening, established)
- Identifies services by port number

### Security and User Monitoring

### 8. Login Tracker (`login_tracker.py`)
- Monitors current user logins (similar to `who`)
- Shows recent login history (similar to `last`)
- Tracks login durations and terminal information
- Includes standalone test function

### 9. Log Monitor (`log_monitor.py`)
- Tails system logs in real-time
- Highlights security-related events
- Configurable to monitor different log files
- Includes built-in regex pattern matchers for common events

### 10. Security Monitor (`security_monitor.py`)
- Tracks failed login attempts
- Monitors sudo usage patterns
- Detects potential brute-force attacks
- Provides security alerts based on configurable thresholds

### Virtualization and Services

### 11. Container Monitor (`container_monitor.py`)
- Monitors Docker and LXD containers
- Shows container resource usage (CPU, memory)
- Displays container status and uptime
- Provides basic container management capabilities

### 12. VM Monitor (`vm_monitor.py`)
- Tracks KVM and VirtualBox virtual machines
- Displays VM status, resource usage, and uptime
- Shows VM network configuration
- Provides basic VM management capabilities

### 13. Service Manager (`service_manager.py`)
- Monitors systemd service status
- Shows service health and uptime
- Allows starting/stopping/restarting services
- Tracks service dependencies and conflicts

## Dashboard Integration

### Dashboard (`dashboard.py`)
- Integrates all modules into a single UI
- Uses `textual` for a rich TUI experience
- Falls back to `rich` library for simpler terminals
- Provides responsive grid layout for all panels
- Supports both TUI and CLI modes

## Component Architecture

Each NetDash module follows a consistent architecture:

1. **Standalone functionality**: Every module can run independently via CLI
2. **Common interface**: Modules expose consistent methods:
   - `get_table()`: Returns a Rich Table object with module data
   - `get_summary()`: Returns a brief summary as a Rich Text or Panel
   - `update()`: Updates the module's internal data

3. **Dashboard integration**: Each module integrates into the dashboard via:
   - A dedicated `DashboardPanel` subclass in `dashboard.py`
   - CSS layout rules defining its size and position
   - An `update_content()` method to refresh panel content

4. **Error handling**: All modules fail gracefully when:
   - Required permissions are missing
   - System resources are unavailable
   - Command execution fails

## Adding a New Module

To add a new monitoring module to NetDash:

1. Create a new Python file in the `netdash` package
2. Implement a class with the following methods:
   - `__init__(self, refresh_interval=1.0)`: Constructor with refresh rate
   - `update(self)`: Collect the latest data
   - `get_table(self)`: Return a Rich Table with the data
   - `get_summary(self)`: Return a brief summary as Rich Text or Panel
   - `main()`: Function for standalone execution

3. Add CLI integration in `__main__.py`:
   - Add the component name to the `--component` choices
   - Add a condition block to import and run the module

4. Add dashboard integration in `dashboard.py`:
   - Create a `DashboardPanel` subclass
   - Add CSS rules for panel positioning
   - Add panel instantiation in the `compose()` method
   - Add panel updates in the `update_panels()` method
   - Add panel initialization in `RichDashboard.__init__()`
   - Add panel rendering in `RichDashboard._update_layout()`

5. Update documentation:
   - Add module description to `README.md`
   - Add module details to `DEVELOPMENT.md`

6. Write tests in the `tests` directory
- Falls back to `rich` if `textual` is unavailable
- Handles graceful shutdown

## Setup and Installation

### Development Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/netdash.git
cd netdash

# Create a virtual environment and install dependencies
python -m venv venv
source venv/bin/activate
pip install -e .

# Generate a sample log file for testing without root
python tools/generate_sample_log.py

# Run the application
python -m netdash
```

### For Normal Use (when packaged)
```bash
# Install from PyPI (future)
pip install netdash

# Or install the Debian package
sudo dpkg -i netdash_0.1.0-1_all.deb

# Run the dashboard
netdash
```

## Running Individual Components
You can run each component separately:

```bash
# Run just the network monitor
python -m netdash --component network

# Run just the login tracker
python -m netdash --component login

# Run just the log monitor
python -m netdash --component log
```

## Building the Debian Package
```bash
# From the project root
dpkg-buildpackage -us -uc
```

## Notes
- Requires Python 3.8+
- Some features require root access but will fail gracefully
- Set `--debug` flag for more verbose output
- Set `--no-color` flag to disable colored output
- The `--rich-only` flag forces Rich-based UI instead of Textual
