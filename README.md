# NetDash

A modular Linux terminal tool similar to `htop`, but focused on **real-time network activity**, **user login monitoring**, and **log-based alerts**.

## Features

### Core Features
- A modular CLI dashboard similar to `htop` with both Textual and Rich UI options
- View live network stats (bandwidth in/out per interface)
- Track current and recent user logins (like `who`, `last`)
- Tail and colorize log events from `/var/log/auth.log`
- System alerts for:
  - Multiple failed login attempts
  - High sudo usage
  - SSH login anomalies

### System Monitoring
- CPU monitoring with per-core statistics
- Memory usage tracking (RAM, swap, buffers/cache)
- Disk usage and I/O monitoring
- System health metrics (uptime, load, temperatures, RAID/SMART)

### Network Monitoring
- Network interface statistics with bandwidth graphs
- Socket tracking (TCP/UDP connections mapped to processes)
- Listening ports visualization with service identification

### Container & Virtualization
- Docker and LXD container monitoring
- Virtual machine inventory and status tracking
- Service management (systemd services status and control)

### Security Features
- Security event monitoring and alerting
- Failed login attempts tracking
- Sudo usage monitoring
- Brute-force detection

## Installation

### From source

```bash
git clone https://github.com/yourusername/netdash.git
cd netdash
pip install -e .
```

### From PyPI (not yet available)

```bash
pip install netdash
```

## Usage

```bash
# Run the full dashboard
netdash

# Run individual components
netdash --component cpu       # CPU monitoring
netdash --component memory    # Memory usage
netdash --component disk      # Disk usage and I/O
netdash --component network   # Network interface stats
netdash --component login     # User login tracking
netdash --component log       # Log monitoring
netdash --component socket    # TCP/UDP socket tracking
netdash --component ports     # Listening ports monitoring
netdash --component system    # System health monitoring
netdash --component service   # Systemd service management
netdash --component container # Container monitoring
netdash --component vm        # Virtual machine monitoring
netdash --component security  # Security monitoring

# Use the Rich-based UI instead of Textual
netdash --rich-only

# Custom log file path
netdash --log-file /path/to/custom.log

# Additional options
netdash --debug     # Enable debug mode
netdash --no-color  # Disable colored output
```

## Development

Requirements:
- Python 3.8+
- Root access for some features (but will fail gracefully)

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT
